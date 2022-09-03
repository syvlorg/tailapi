{
    description = "A python application and library to interact with the tailscale api!";
    inputs = rec {
        settings.url = github:sylvorg/settings;
        titan.url = github:syvlorg/titan;
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
        callPackage = { stdenv
            , pythonOlder
            , oreo
            , pname
            , magicattr
            , requests
            , rapidfuzz
        }: j.mkPythonPackage self.pkgs.${stdenv.targetPlatform.system}.Pythons.${self.type}.pkgs (rec {
            owner = "syvlorg";
            inherit pname;
            disabled = pythonOlder "3.10";
            src = ./.;
            propagatedBuildInputs = [ oreo magicattr requests rapidfuzz ];
            postPatch = ''
                substituteInPlace pyproject.toml --replace "oreo = { git = \"https://github.com/${owner}/oreo.git\", branch = \"main\" }" ""
                substituteInPlace setup.py --replace "'oreo @ git+https://github.com/${owner}/oreo.git@main'," ""
            '';
            meta = {
                description = "A python application and library to interact with the tailscale api!";
            };
        });
    };
}
