with builtins; let
    pkgs = import (fetchGit { url = "https://github.com/shadowrylander/nixpkgs"; ref = "j"; }) {};
in with pkgs; mkShell {
    buildInputs = with python310Packages; [ xonsh python310 (tailapi.overridePythonAttrs (prev: {
        src = ./.;
    })) ];
    shellHook = ''
        export TAILSCALE_APIKEY=$(pass show keys/api/tailscale/jeet.ray)
        exec xonsh
    '';
}