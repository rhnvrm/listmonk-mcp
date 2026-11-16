{
  description = "Listmonk MCP Server development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        
        python = pkgs.python313;
        
        pythonEnv = python.withPackages (ps: with ps; [
          pip
          setuptools
          wheel
        ]);
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            # Python and package management
            pythonEnv
            uv
            
            # Development tools
            git
            gnumake
            go
            
            # Testing and formatting
            ruff
            
            # JSON tools for config
            jq
            
            # Optional: helpful tools
            curl
            httpie
          ];

          shellHook = ''
            echo "🚀 Listmonk MCP Server dev environment"
            echo "Python: $(python --version)"
            echo "UV: $(uv --version)"
            
            # Setup uv virtual environment if it doesn't exist
            if [ ! -d ".venv" ]; then
              echo "Creating virtual environment with uv..."
              uv venv
            fi
            
            # Activate virtual environment
            source .venv/bin/activate
            
            # Install dependencies if pyproject.toml exists
            if [ -f "pyproject.toml" ]; then
              echo "Installing dependencies..."
              uv sync
            fi
            
            echo "✅ Development environment ready!"
          '';

          # Environment variables
          PYTHONPATH = ".";
          UV_PYTHON = "${python}/bin/python";
        };
      });
}