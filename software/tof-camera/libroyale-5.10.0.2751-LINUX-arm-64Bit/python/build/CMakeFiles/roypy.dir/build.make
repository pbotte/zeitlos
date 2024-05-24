# CMAKE generated file: DO NOT EDIT!
# Generated by "Unix Makefiles" Generator, CMake Version 3.25

# Delete rule output on recipe failure.
.DELETE_ON_ERROR:

#=============================================================================
# Special targets provided by cmake.

# Disable implicit rules so canonical targets will work.
.SUFFIXES:

# Disable VCS-based implicit rules.
% : %,v

# Disable VCS-based implicit rules.
% : RCS/%

# Disable VCS-based implicit rules.
% : RCS/%,v

# Disable VCS-based implicit rules.
% : SCCS/s.%

# Disable VCS-based implicit rules.
% : s.%

.SUFFIXES: .hpux_make_needs_suffix_list

# Command-line flag to silence nested $(MAKE).
$(VERBOSE)MAKESILENT = -s

#Suppress display of executed commands.
$(VERBOSE).SILENT:

# A target that is always out of date.
cmake_force:
.PHONY : cmake_force

#=============================================================================
# Set environment variables for the build.

# The shell in which to execute make rules.
SHELL = /bin/sh

# The CMake executable.
CMAKE_COMMAND = /usr/bin/cmake

# The command to remove a file.
RM = /usr/bin/cmake -E rm -f

# Escaping for special characters.
EQUALS = =

# The top-level source directory on which CMake was run.
CMAKE_SOURCE_DIR = /home/pi/zeitlos/software/roy-tof-camera/libroyale-5.10.0.2751-LINUX-arm-64Bit/python/swig

# The top-level build directory on which CMake was run.
CMAKE_BINARY_DIR = /home/pi/zeitlos/software/roy-tof-camera/libroyale-5.10.0.2751-LINUX-arm-64Bit/python/build

# Include any dependencies generated for this target.
include CMakeFiles/roypy.dir/depend.make
# Include any dependencies generated by the compiler for this target.
include CMakeFiles/roypy.dir/compiler_depend.make

# Include the progress variables for this target.
include CMakeFiles/roypy.dir/progress.make

# Include the compile flags for this target's objects.
include CMakeFiles/roypy.dir/flags.make

CMakeFiles/roypy.dir/bin/roypyPYTHON_wrap.cxx.o: CMakeFiles/roypy.dir/flags.make
CMakeFiles/roypy.dir/bin/roypyPYTHON_wrap.cxx.o: bin/roypyPYTHON_wrap.cxx
CMakeFiles/roypy.dir/bin/roypyPYTHON_wrap.cxx.o: CMakeFiles/roypy.dir/compiler_depend.ts
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green --progress-dir=/home/pi/zeitlos/software/roy-tof-camera/libroyale-5.10.0.2751-LINUX-arm-64Bit/python/build/CMakeFiles --progress-num=$(CMAKE_PROGRESS_1) "Building CXX object CMakeFiles/roypy.dir/bin/roypyPYTHON_wrap.cxx.o"
	/usr/bin/c++ $(CXX_DEFINES) -DROYALE_ACTIVATE_NUMPY $(CXX_INCLUDES) $(CXX_FLAGS) -MD -MT CMakeFiles/roypy.dir/bin/roypyPYTHON_wrap.cxx.o -MF CMakeFiles/roypy.dir/bin/roypyPYTHON_wrap.cxx.o.d -o CMakeFiles/roypy.dir/bin/roypyPYTHON_wrap.cxx.o -c /home/pi/zeitlos/software/roy-tof-camera/libroyale-5.10.0.2751-LINUX-arm-64Bit/python/build/bin/roypyPYTHON_wrap.cxx

CMakeFiles/roypy.dir/bin/roypyPYTHON_wrap.cxx.i: cmake_force
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green "Preprocessing CXX source to CMakeFiles/roypy.dir/bin/roypyPYTHON_wrap.cxx.i"
	/usr/bin/c++ $(CXX_DEFINES) -DROYALE_ACTIVATE_NUMPY $(CXX_INCLUDES) $(CXX_FLAGS) -E /home/pi/zeitlos/software/roy-tof-camera/libroyale-5.10.0.2751-LINUX-arm-64Bit/python/build/bin/roypyPYTHON_wrap.cxx > CMakeFiles/roypy.dir/bin/roypyPYTHON_wrap.cxx.i

CMakeFiles/roypy.dir/bin/roypyPYTHON_wrap.cxx.s: cmake_force
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green "Compiling CXX source to assembly CMakeFiles/roypy.dir/bin/roypyPYTHON_wrap.cxx.s"
	/usr/bin/c++ $(CXX_DEFINES) -DROYALE_ACTIVATE_NUMPY $(CXX_INCLUDES) $(CXX_FLAGS) -S /home/pi/zeitlos/software/roy-tof-camera/libroyale-5.10.0.2751-LINUX-arm-64Bit/python/build/bin/roypyPYTHON_wrap.cxx -o CMakeFiles/roypy.dir/bin/roypyPYTHON_wrap.cxx.s

# Object files for target roypy
roypy_OBJECTS = \
"CMakeFiles/roypy.dir/bin/roypyPYTHON_wrap.cxx.o"

# External object files for target roypy
roypy_EXTERNAL_OBJECTS =

_roypy.so: CMakeFiles/roypy.dir/bin/roypyPYTHON_wrap.cxx.o
_roypy.so: CMakeFiles/roypy.dir/build.make
_roypy.so: /home/pi/zeitlos/software/roy-tof-camera/libroyale-5.10.0.2751-LINUX-arm-64Bit/bin/libroyale.so.5.10.0
_roypy.so: /usr/lib/aarch64-linux-gnu/libpython3.11.so
_roypy.so: CMakeFiles/roypy.dir/link.txt
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green --bold --progress-dir=/home/pi/zeitlos/software/roy-tof-camera/libroyale-5.10.0.2751-LINUX-arm-64Bit/python/build/CMakeFiles --progress-num=$(CMAKE_PROGRESS_2) "Linking CXX shared module _roypy.so"
	$(CMAKE_COMMAND) -E cmake_link_script CMakeFiles/roypy.dir/link.txt --verbose=$(VERBOSE)

# Rule to build all files generated by this target.
CMakeFiles/roypy.dir/build: _roypy.so
.PHONY : CMakeFiles/roypy.dir/build

CMakeFiles/roypy.dir/clean:
	$(CMAKE_COMMAND) -P CMakeFiles/roypy.dir/cmake_clean.cmake
.PHONY : CMakeFiles/roypy.dir/clean

CMakeFiles/roypy.dir/depend:
	cd /home/pi/zeitlos/software/roy-tof-camera/libroyale-5.10.0.2751-LINUX-arm-64Bit/python/build && $(CMAKE_COMMAND) -E cmake_depends "Unix Makefiles" /home/pi/zeitlos/software/roy-tof-camera/libroyale-5.10.0.2751-LINUX-arm-64Bit/python/swig /home/pi/zeitlos/software/roy-tof-camera/libroyale-5.10.0.2751-LINUX-arm-64Bit/python/swig /home/pi/zeitlos/software/roy-tof-camera/libroyale-5.10.0.2751-LINUX-arm-64Bit/python/build /home/pi/zeitlos/software/roy-tof-camera/libroyale-5.10.0.2751-LINUX-arm-64Bit/python/build /home/pi/zeitlos/software/roy-tof-camera/libroyale-5.10.0.2751-LINUX-arm-64Bit/python/build/CMakeFiles/roypy.dir/DependInfo.cmake --color=$(COLOR)
.PHONY : CMakeFiles/roypy.dir/depend
