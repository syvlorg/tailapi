with builtins;
let
  flake = import ./.;
  inherit (flake.x86_64-linux) devShells pkgs;
in with flake.lib;
iron.fold.shell pkgs [
  devShells.makefile
  (with pkgs;
    mkShell {
      shellHook = ''
        export TEST_TAILSCALE_ATK=$(${pkgs.pass}/bin/pass show keys/oauth/tailscale/undrjarn.org.github/master)
        pytest --suppress-no-test-exit-code --dist loadgroup -n auto
        exit
      '';
    })
]
