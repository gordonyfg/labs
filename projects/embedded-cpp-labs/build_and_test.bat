@echo off

:: Clean the build directory
if exist build (
    rmdir /s /q build
)
mkdir build
cd build

:: Configure the project with CMake
echo Configuring the project...
cmake -G "MinGW Makefiles" -DCMAKE_TOOLCHAIN_FILE=C:/msys64/mingw64/bin/vcpkg/scripts/buildsystems/vcpkg.cmake -DVCPKG_TARGET_TRIPLET=x64-mingw-dynamic ..

if %errorlevel% neq 0 (
    echo CMake configuration failed!
    exit /b %errorlevel%
)

:: Build the project
echo Building the project...
cmake --build . --config Release

if %errorlevel% neq 0 (
    echo Build failed!
    exit /b %errorlevel%
)

:: Run tests using CTest
echo Running tests...
ctest -C Release --output-on-failure

if %errorlevel% neq 0 (
    echo Tests failed!
    exit /b %errorlevel%
)

:: Run the test binary directly (optional)
echo Running test binary...
if exist tests.exe (
    tests.exe
)

echo Build and tests completed successfully!
pause
