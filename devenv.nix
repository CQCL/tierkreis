{ pkgs, lib, ... }:

{

  packages = [
    pkgs.just
    pkgs.graphviz
  ] ++ lib.optionals pkgs.stdenv.isDarwin (with pkgs.darwin.apple_sdk; [
    frameworks.CoreServices
    frameworks.CoreFoundation
    frameworks.Security
    frameworks.SystemConfiguration
  ]);

  git-hooks.hooks = {
    pyright.enable = true;
    ruff.enable = true;
    ruff-format.enable = true;
  };

  # https://devenv.sh/languages/
  languages.python = {
    enable = true;
    uv.enable = true;
  };

  languages.rust.enable = true;

  languages.javascript = {
    enable = true;
    bun.enable = true;
    bun.install.enable = true;
    directory = "./tierkreis_visualization";
  };

  # This allows building the type-check (pyo3) module on MacOSX "Apple Silicon"
  enterShell =
    if pkgs.stdenv.isDarwin && pkgs.stdenv.isAarch64 then ''
      export RUSTFLAGS="$RUSTFLAGS -C link-arg=-undefined -C link-arg=dynamic_lookup"
    '' else '''';

  scripts.sbatch = {
    exec = ''
      if [ -z "$1" ]; then
        echo "Usage: sbatch <path_to_slurm_script>"
        echo "Any further arguments will be discarded"
        exit 1
      fi
      SCRIPT_FILE=$(basename "$1")
      docker cp "$1" slurmctld:/data/"$SCRIPT_FILE"
      docker exec slurmctld sbatch --chdir=/data /data/"$SCRIPT_FILE"
    '';
  };

}
