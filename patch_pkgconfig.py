import sys

content = open('/opt/palace-src/palace/cmake/PkgConfigHelpers.cmake').read()

old_petsc = """  try_run(
    PETSC_TEST_EXITCODE
    PETSC_TEST_COMPILED
    ${PETSC_LIB_TEST_DIR}
    ${PETSC_LIB_TEST_CPP}
    CMAKE_FLAGS -DCMAKE_C_COMPILER=${CMAKE_C_COMPILER} -DCMAKE_CXX_COMPILER=${CMAKE_CXX_COMPILER}
    LINK_LIBRARIES ${_petsc_target}
    COMPILE_OUTPUT_VARIABLE PETSC_TEST_COMPILE_OUTPUT
    RUN_OUTPUT_VARIABLE PETSC_TEST_OUTPUT
  )
  if(PETSC_TEST_COMPILED AND PETSC_TEST_EXITCODE EQUAL 0)"""

new_petsc = """  try_compile(
    PETSC_TEST_COMPILED
    ${PETSC_LIB_TEST_DIR}
    ${PETSC_LIB_TEST_CPP}
    CMAKE_FLAGS -DCMAKE_C_COMPILER=${CMAKE_C_COMPILER} -DCMAKE_CXX_COMPILER=${CMAKE_CXX_COMPILER}
    LINK_LIBRARIES ${_petsc_target}
    OUTPUT_VARIABLE PETSC_TEST_COMPILE_OUTPUT
  )
  if(PETSC_TEST_COMPILED)"""

old_slepc = """  try_run(
    SLEPC_TEST_EXITCODE
    SLEPC_TEST_COMPILED
    ${SLEPC_LIB_TEST_DIR}
    ${SLEPC_LIB_TEST_CPP}
    LINK_LIBRARIES ${_slepc_target}
    COMPILE_OUTPUT_VARIABLE SLEPC_TEST_COMPILE_OUTPUT
    RUN_OUTPUT_VARIABLE SLEPC_TEST_OUTPUT
  )
  # message(STATUS "SLEPC_TEST_COMPILE_OUTPUT: ${SLEPC_TEST_COMPILE_OUTPUT}")
  # message(STATUS "SLEPC_TEST_OUTPUT: ${SLEPC_TEST_OUTPUT}")
  if(SLEPC_TEST_COMPILED AND SLEPC_TEST_EXITCODE EQUAL 0)"""

new_slepc = """  try_compile(
    SLEPC_TEST_COMPILED
    ${SLEPC_LIB_TEST_DIR}
    ${SLEPC_LIB_TEST_CPP}
    LINK_LIBRARIES ${_slepc_target}
    OUTPUT_VARIABLE SLEPC_TEST_COMPILE_OUTPUT
  )
  # message(STATUS "SLEPC_TEST_COMPILE_OUTPUT: ${SLEPC_TEST_COMPILE_OUTPUT}")
  if(SLEPC_TEST_COMPILED)"""

result = content.replace(old_petsc, new_petsc).replace(old_slepc, new_slepc)
if result == content:
    print("ERROR: no replacements made", file=sys.stderr)
    sys.exit(1)
open('/opt/palace-src/palace/cmake/PkgConfigHelpers.cmake', 'w').write(result)
print("Patch applied successfully")
