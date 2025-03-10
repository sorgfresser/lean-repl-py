#!/bin/bash
# Blatantly copied from https://github.com/leanprover/lean-action/blob/main/scripts/install_elan.sh

# Group logging using the ::group:: workflow command
echo "::group::Elan Installation Output"

set -o pipefail
curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf |
  sh -s -- -y --default-toolchain stable
rm -f elan-init

echo "$HOME/.elan/bin" >>"$GITHUB_PATH"
"$HOME"/.elan/bin/lean --version
"$HOME"/.elan/bin/lake --version

echo "::endgroup::"
echo
