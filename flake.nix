{
    description = "A python application and library to interact with the tailscale api!";
    inputs = rec {
        settings.url = github:sylvorg/settings;
        flake-utils.url = github:numtide/flake-utils;
        flake-compat = {
            url = "github:edolstra/flake-compat";
            flake = false;
        };
        py3pkg-oreo.url = github:syvlorg/oreo;
        py3pkg-pytest-hy.url = github:syvlorg/pytest-hy;
    };
    outputs = inputs@{ self, flake-utils, settings, ... }: with builtins; with settings.lib; with flake-utils.lib; settings.mkOutputs rec {
        inherit inputs;
        type = "hy";
        pname = "tailapi";
        isApp = true;
        extras.global.shellHook = ''
            export TAILSCALE_APIKEY=$(pass show keys/api/tailscale/jeet.ray)
            export TAILSCALE_DOMAIN="sylvorg.github"
        '';
        callPackage = { buildPythonPackage
            , fetchFromGitHub
            , pythonOlder
            , poetry-core
            , oreo
            , pname
            , pytestCheckHook
            , pytest-hy
            , pytest-randomly
            , pytest-parametrized
            , pytest-custom_exit_code
            , magicattr
            , requests
            , rapidfuzz
        }: let owner = "syvlorg"; in buildPythonPackage rec {
            inherit pname;
            version = "1.0.0.0";
            format = "pyproject";
            disabled = pythonOlder "3.10";
            src = ./.;
            buildInputs = [ poetry-core ];
            nativeBuildInputs = buildInputs;
            propagatedBuildInputs = [ oreo magicattr requests rapidfuzz ];
            pythonImportsCheck = [ pname ];
            checkInputs = [ pytestCheckHook pytest-hy pytest-randomly pytest-parametrized pytest-custom_exit_code ];
            pytestFlagsArray = toList "--suppress-no-test-exit-code";
            postPatch = ''
                substituteInPlace pyproject.toml --replace "oreo = { git = \"https://github.com/${owner}/oreo.git\", branch = \"main\" }" ""
                substituteInPlace setup.py --replace "'oreo @ git+https://github.com/${owner}/oreo.git@main'," ""
            '';
            meta = {
                description = "A python application and library to interact with the tailscale api!";
                homepage = "https://github.com/${owner}/${pname}";
            };
        };
    };
}
