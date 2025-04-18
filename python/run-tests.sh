#!/bin/bash -x

set -uo pipefail

# Colors for terminal output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Setting up test environment...${NC}"

# Set working directory to the script location
cd "$(dirname "$0")" || exit

# Make sure we're using the correct Python path
# Updated to remove app directory reference since index.py is now directly in api folder
parent=$(cd .. && pwd)
current=$(pwd)
export PYTHONPATH="$parent:$current"
# Debug: Show Python path
echo -e "${YELLOW}PYTHONPATH: $PYTHONPATH${NC}"

# Debug: Show directory structure
echo -e "${YELLOW}Directory structure:${NC}"
find . -type f -name "*.py" | grep -v "__pycache__" | sort | head -n 20

# Check for virtual environment and activate if present
if [ -d "../venv" ]; then
    source ../venv/bin/activate
    echo -e "${GREEN}Activated virtual environment.${NC}"
fi

# Check if required packages are installed
echo -e "${YELLOW}Installing/upgrading required packages...${NC}"

pip install -r ../requirements.txt
pip install -r requirements-dev.txt

# Debug: Print the file content of conftest.py to understand the import issue
if [ -f "tests/conftest.py" ]; then
    echo -e "${YELLOW}Content of tests/conftest.py:${NC}"
    head -n 20 tests/conftest.py
fi

# Parse command line arguments
COVERAGE=1
VERBOSE=1
SPECIFIC_TEST=""

for arg in "$@"; do
    case $arg in
        --no-cov|--no-coverage)
        COVERAGE=0
        shift
        ;;
        --quiet|--no-verbose)
        VERBOSE=0
        shift
        ;;
        -h|--help)
        echo "Usage: ./run-tests.sh [options] [test_path]"
        echo "Options:"
        echo "  --cov, --coverage  Enable coverage reporting."
        echo "  -v, --verbose      Run tests in verbose mode."
        echo "  -h, --help         Show this help message."
        exit 0
        ;;
        *)
        SPECIFIC_TEST="$arg"
        shift
        ;;
    esac
done

# Build the pytest command with proper arguments
PYTEST_CMD="python -m pytest"

# Add the test path
if [ -z "$SPECIFIC_TEST" ]; then
    echo -e "${YELLOW}Running all tests...${NC}"
    PYTEST_CMD="$PYTEST_CMD tests/"
else
    echo -e "${YELLOW}Running specific test: $SPECIFIC_TEST${NC}"
    PYTEST_CMD="$PYTEST_CMD $SPECIFIC_TEST"
fi

# Add verbose flag if requested
if [ $VERBOSE -eq 1 ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

# Add coverage flags if requested
if [ $COVERAGE -eq 1 ]; then
    # Updated to include api/index.py in coverage report with specific exclusions
    PYTEST_CMD="$PYTEST_CMD --cov=app --cov=api --cov-report=term-missing --cov-config=.coveragerc"
    
    # Always add -s to see output from tests
    PYTEST_CMD="$PYTEST_CMD -s"
else
    # Add minimal coverage for api/index.py even when not explicitly requested
    PYTEST_CMD="$PYTEST_CMD --cov=api --cov-report=term-missing:skip-covered"
fi

# Add -s to show print outputs which can help with debugging
PYTEST_CMD="$PYTEST_CMD -s"

# Run the tests
eval $PYTEST_CMD

# Check the test result
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${RED}✗ Some tests failed.${NC}"
    exit 1
fi
