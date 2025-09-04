{
  description = "Target Process MCP Server - Model Context Protocol server for Target Process API";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        
        # Python version to use
        python = pkgs.python312;
        pythonPackages = python.pkgs;
        
        # Build the Target Process MCP package
        targetprocess-mcp = pythonPackages.buildPythonApplication rec {
          pname = "targetprocess-mcp";
          version = "0.1.0";
          
          src = ./.;
          
          pyproject = true;
          
          nativeBuildInputs = with pythonPackages; [
            setuptools
            wheel
          ];
          
          propagatedBuildInputs = with pythonPackages; [
            mcp
            httpx
            python-dotenv
          ];
          
          # Ensure the module can be imported
          pythonImportsCheck = [ "targetprocess_mcp" ];
          
          meta = with pkgs.lib; {
            description = "Model Context Protocol server for Target Process API";
            homepage = "https://github.com/Veraticus/targetprocess-mcp";
            license = licenses.mit;
            maintainers = with maintainers; [ ];
            platforms = platforms.unix;
          };
        };
        
      in
      {
        # Packages
        packages = {
          inherit targetprocess-mcp;
          default = targetprocess-mcp;
        };
        
        # Development shell
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            python
            pythonPackages.pip
            pythonPackages.black
            pythonPackages.pytest
            pythonPackages.pytest-asyncio
            pythonPackages.mcp
            pythonPackages.httpx
            pythonPackages.python-dotenv
            
            # Development tools
            git
            jq
          ];
          
          shellHook = ''
            echo "Target Process MCP development environment"
            echo "Available commands:"
            echo "  python src/targetprocess_mcp.py  - Run the MCP server"
            echo "  black src/                        - Format code"
            echo "  pytest                            - Run tests"
            echo "  nix build                         - Build with Nix"
            echo ""
            echo "Python version: ${python.version}"
          '';
        };
        
        # App for nix run
        apps.default = {
          type = "app";
          program = "${targetprocess-mcp}/bin/targetprocess-mcp";
        };
      }
    );
}