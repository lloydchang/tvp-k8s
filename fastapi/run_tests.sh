#!/bin/bash

# Colors for terminal output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Setting up test environment...${NC}"

# Set working directory to the script location
cd "$(dirname "$0")"

# Make sure we're using the correct Python path
export PYTHONPATH=$(cd .. && pwd):$(pwd)

# Check for virtual environment and activate if present
if [ -d "../venv" ]; then
    source ../venv/bin/activate
    echo -e "${GREEN}Activated virtual environment.${NC}"
fi

# Check if required packages are installed
echo -e "${YELLOW}Installing/upgrading required packages...${NC}"

# First uninstall any existing pytest and pytest-asyncio to avoid version conflicts
python -m pip uninstall -y pytest pytest-asyncio pytest-cov

# Install specific compatible versions
python -m pip install pytest==7.3.1 pytest-asyncio==0.21.1 pytest-cov==4.1.0 httpx pyyaml kubernetes fastapi uvicorn -q

# Parse command line arguments
COVERAGE=""
VERBOSE=""
SPECIFIC_TEST=""

for arg in "$@"; do
    case $arg in
        --cov|--coverage)
        COVERAGE="--cov=. --cov-report=term-missing"
        shift
        ;;
        -v|--verbose)
        VERBOSE="-v"
        shift
        ;;
        *)
        SPECIFIC_TEST="$arg"
        shift
        ;;
    esac
done

# Run the tests
if [ -z "$SPECIFIC_TEST" ]; then
    echo -e "${YELLOW}Running all tests...${NC}"
    python -m pytest tests/ $VERBOSE $COVERAGE
else
    echo -e "${YELLOW}Running specific test: $SPECIFIC_TEST${NC}"
    python -m pytest $SPECIFIC_TEST $VERBOSE $COVERAGE
fi

# Check the test result
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${RED}✗ Some tests failed.${NC}"
    exit 1
fi
