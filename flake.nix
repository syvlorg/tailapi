{
  nixConfig = {
    # Adapted From: https://github.com/divnix/digga/blob/main/examples/devos/flake.nix#L4
    accept-flake-config = true;
    auto-optimise-store = true;
    builders-use-substitutes = true;
    cores = 0;
    extra-experimental-features =
      "nix-command flakes impure-derivations recursive-nix";
    fallback = true;
    flake-registry =
      "https://raw.githubusercontent.com/syvlorg/flake-registry/master/flake-registry.json";
    keep-derivations = true;
    keep-outputs = true;
    max-free = 1073741824;
    min-free = 262144000;
    show-trace = true;
    trusted-public-keys = [
      "cache.nixos.org-1:6NCHdD59X431o0gWypbMrAURkbJ16ZPMQFGspcDShjY="
      "nix-community.cachix.org-1:mB9FSh9qf2dCimDSUo8Zy7bkq5CX+/rkCWyvRCYg3Fs="
      "nickel.cachix.org-1:ABoCOGpTJbAum7U6c+04VbjvLxG9f0gJP5kYihRRdQs="
      "sylvorg.cachix.org-1:xd1jb7cDkzX+D+Wqt6TemzkJH9u9esXEFu1yaR9p8H8="
    ];
    trusted-substituters = [
      "https://cache.nixos.org/"
      "https://nix-community.cachix.org"
      "https://nickel.cachix.org"
      "https://sylvorg.cachix.org"
    ];
    warn-dirty = false;
  };
  description =
    "A python application and library to interact with the tailscale api!";
  inputs = rec {
    bundle = {
      url = "https://github.com/sylvorg/bundle.git";
      type = "git";
      submodules = true;
    };
    valiant.follows = "bundle/valiant";
    nixpkgs.follows = "bundle/nixpkgs";

    pyPkg-oreo.url =
      "git+https://github.com/syvlorg/oreo.git";

    flake-utils.url = "github:numtide/flake-utils";
    flake-compat = {
      url = "github:edolstra/flake-compat";
      flake = false;
    };
    magicattr = {
      url = "github:frmdstryr/magicattr";
      flake = false;
    };
  };
  outputs = inputs@{ self, flake-utils, ... }:
    with builtins;
    with inputs.bundle.lib;
    with flake-utils.lib;
    inputs.bundle.mkOutputs.python rec {
      inherit inputs self;
      pname = "tailapi";
      doCheck = true;
      callPackageset.python.magicattr = let pname = "magicattr";
      in { buildPythonPackage, pytestCheckHook }:
      buildPythonPackage rec {
        inherit pname;
        version = iron.pyVersion src;
        src = inputs.${pname};
        doCheck = false;
        pythonImportsCheck = [ pname ];
        checkInputs = [ pytestCheckHook ];
        meta = {
          description =
            "A getattr and setattr that works on nested objects, lists, dicts, and any combination thereof without resorting to eval";
          homepage = "https://github.com/${Inputs.${pname}.owner}/${pname}";
          license = licenses.mit;
        };
      };
      callPackage = { callPackage, magicattr, requests }:
        callPackage (iron.mkPythonPackage {
          inherit self inputs;
          package = {
            doCheck = false;
            src = ./.;
            propagatedBuildInputs = [ magicattr requests ];
            postPatch = ''
              substituteInPlace pyproject.toml \
                --replace "oreo = { git = \"https://github.com/syvlorg/oreo.git\", branch = \"main\" }" ""
              substituteInPlace setup.py \
                --replace "'oreo @ git+https://github.com/syvlorg/oreo.git@main'," "" || :
            '';
            meta.description =
              "A python application and library to interact with the tailscale api!";
          };
        }) { };
    } { isApp = true; };
}
