with import /home/shadowrylander/nixpkgs {}; mkShell {
    buildInputs = with python310Packages; [ requests (oreo.overridePythonAttrs (prev: {
        src = /home/shadowrylander/shadowrylander/sylveon/oreo;
    })) ];
    shellHook = ''
        export TAILSCALE_APIKEY=$(pass show keys/api/tailscale/jeet.ray)
    '';
}
