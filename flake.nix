{
  description = "Static site tooling for pineapplehunter";

  inputs.nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
  inputs.flake-parts.url = "github:hercules-ci/flake-parts";

  outputs =
    { flake-parts, ... }@inputs:
    flake-parts.lib.mkFlake { inherit inputs; } {
      systems = [
        "aarch64-darwin"
        "aarch64-linux"
        "x86_64-linux"
      ];

      perSystem =
        { pkgs, system, ... }:
        {
          _module.args.pkgs = import inputs.nixpkgs {
            inherit system;
            overlays = [
              # Add overlays as needed
            ];
          };

          devShells.default = pkgs.mkShell {
            packages = with pkgs; [
              tailwindcss_4
              (python3.withPackages (ps: with ps; [ jinja2 markdown-it-py ninja pillow pyyaml ]))
            ];
          };

          # Use nixfmt for all nix files
          formatter = pkgs.nixfmt-tree;

          # Uncomment to build any package with `nix build .#package`
          #legacyPackages = pkgs;
        };
    };
}
