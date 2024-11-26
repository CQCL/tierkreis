# run from root directory
export DOCS_DIR=$(pwd)/python/docs
mkdir -p $DOCS_DIR/build

touch $DOCS_DIR/build/.nojekyll  # Disable jekyll to keep files starting with underscores

sphinx-build -b html $DOCS_DIR/api-docs $DOCS_DIR/build/api-docs
