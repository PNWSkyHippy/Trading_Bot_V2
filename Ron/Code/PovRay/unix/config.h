/* unix/config.h.  Generated from config.h.in by configure.  */
/* unix/config.h.in.  Generated from configure.ac by autoheader.  */

/* Build architecture. */
#define BUILD_ARCH "x86_64-pc-linux-gnu"

/* Build for x86 or x86-64 architecture */
#define BUILD_X86 /**/

/* Supported image formats. */
#define BUILTIN_IMG_FORMATS "gif tga iff ppm pgm hdr png jpeg tiff openexr"

/* I/O restrictions. */
#define BUILTIN_IO_RESTRICTIONS "enabled"

/* X Window display. */
#define BUILTIN_XWIN_DISPLAY "enabled (using SDL)"

/* Who compiled this binary. */
#define BUILT_BY "SkyHippy"

/* Host platform. */
#define BUILT_FOR "x86_64-pc-linux-gnu (using -march=native)"

/* See source/backend/support/octree.cpp for details. */
/* #undef C99_COMPATIBLE_RADIOSITY */

/* Compiler vendor. */
#define COMPILER_VENDOR "gnu"

/* Compiler version. */
#define COMPILER_VERSION "g++ 13"

/* Compiler flags. */
#define CXXFLAGS "-pipe -Wno-multichar -Wno-write-strings -fno-enforce-eh-specs -Wno-non-template-friend -s -O3 -ffast-math -march=native -pthread"

/* Define to 1 if you have the `asinh' function. */
#define HAVE_ASINH 1

/* define if the Boost library is available */
#define HAVE_BOOST /**/

/* define if the Boost::Thread library is available */
#define HAVE_BOOST_THREAD /**/

/* Define to 1 if the system has the type `clockid_t'. */
#define HAVE_CLOCKID_T 1

/* Define to 1 if you have the `clock_gettime' function. */
#define HAVE_CLOCK_GETTIME 1

/* Define to 1 if you have the <cmath> header file. */
#define HAVE_CMATH 1

/* Define to 1 if you have the `copysign' function. */
/* #undef HAVE_COPYSIGN */

/* define if the compiler supports basic C++11 syntax */
#define HAVE_CXX11 1

/* Define to 1 if you have the declaration of `CLOCK_MONOTONIC', and to 0 if
   you don't. */
#define HAVE_DECL_CLOCK_MONOTONIC 1

/* Define to 1 if you have the declaration of `CLOCK_PROCESS_CPUTIME_ID', and
   to 0 if you don't. */
#define HAVE_DECL_CLOCK_PROCESS_CPUTIME_ID 1

/* Define to 1 if you have the declaration of `CLOCK_REALTIME', and to 0 if
   you don't. */
#define HAVE_DECL_CLOCK_REALTIME 1

/* Define to 1 if you have the declaration of `CLOCK_THREAD_CPUTIME_ID', and
   to 0 if you don't. */
#define HAVE_DECL_CLOCK_THREAD_CPUTIME_ID 1

/* Define to 1 if you have the declaration of `RUSAGE_LWP', and to 0 if you
   don't. */
#define HAVE_DECL_RUSAGE_LWP 1

/* Define to 1 if you have the declaration of `RUSAGE_SELF', and to 0 if you
   don't. */
#define HAVE_DECL_RUSAGE_SELF 1

/* Define to 1 if you have the declaration of `RUSAGE_THREAD', and to 0 if you
   don't. */
#define HAVE_DECL_RUSAGE_THREAD 1

/* infinities can be identified by comparison to the maximum value */
#define HAVE_EMULATED_ISINF /**/

/* NaNs can be identified by comparison to themselves */
/* #undef HAVE_EMULATED_ISNAN */

/* Define to 1 if you have the `getcwd' function. */
#define HAVE_GETCWD 1

/* Define to 1 if you have the `getrusage' function. */
#define HAVE_GETRUSAGE 1

/* Define to 1 if you have the `gettimeofday' function. */
#define HAVE_GETTIMEOFDAY 1

/* Define to 1 if you have the `ilogb' function. */
/* #undef HAVE_ILOGB */

/* Define to 1 if you have the `ilogbf' function. */
/* #undef HAVE_ILOGBF */

/* infinite floating point values are supported */
#define HAVE_INF /**/

/* Define to 1 if you have the <inttypes.h> header file. */
#define HAVE_INTTYPES_H 1

/* intinities can be identified using global isinf() */
/* #undef HAVE_ISINF */

/* NaNs can be identified using global isnan() */
/* #undef HAVE_ISNAN */

/* Define to 1 if you have the `m' library (-lm). */
#define HAVE_LIBM 1

/* Define to 1 if you have the `mkl' library (-lmkl). */
/* #undef HAVE_LIBMKL */

/* Define to 1 if you have the `rt' library (-lrt). */
#define HAVE_LIBRT 1

/* Define to 1 if you have the `SDL' library (-lSDL). */
#define HAVE_LIBSDL 1

/* Define to 1 if you have the `Xpm' library (-lXpm). */
/* #undef HAVE_LIBXPM */

/* Define to 1 if you have the <limits> header file. */
#define HAVE_LIMITS 1

/* Define to 1 if you have the <limits.h> header file. */
#define HAVE_LIMITS_H 1

/* Define to 1 if you have the `logb' function. */
/* #undef HAVE_LOGB */

/* Define to 1 if you have the `logbf' function. */
/* #undef HAVE_LOGBF */

/* Define to 1 if you have the <memory.h> header file. */
#define HAVE_MEMORY_H 1

/* NaN floating point values are supported */
/* #undef HAVE_NAN */

/* Define to 1 if you have the `nanosleep' function. */
#define HAVE_NANOSLEEP 1

/* Define if you have POSIX threads libraries and header files. */
#define HAVE_PTHREAD 1

/* Have PTHREAD_PRIO_INHERIT. */
#define HAVE_PTHREAD_PRIO_INHERIT 1

/* Define to 1 if you have the `readlink' function. */
#define HAVE_READLINK 1

/* Define to 1 if you have the <stdint.h> header file. */
#define HAVE_STDINT_H 1

/* Define to 1 if you have the <stdlib.h> header file. */
#define HAVE_STDLIB_H 1

/* intinities can be identified using std::isinf() */
/* #undef HAVE_STD_ISINF */

/* NaNs can be identified using std::isnan() */
/* #undef HAVE_STD_ISNAN */

/* Define to 1 if you have the <strings.h> header file. */
#define HAVE_STRINGS_H 1

/* Define to 1 if you have the <string.h> header file. */
#define HAVE_STRING_H 1

/* Define to 1 if you have the <sys/resource.h> header file. */
#define HAVE_SYS_RESOURCE_H 1

/* Define to 1 if you have the <sys/stat.h> header file. */
#define HAVE_SYS_STAT_H 1

/* Define to 1 if you have the <sys/time.h> header file. */
#define HAVE_SYS_TIME_H 1

/* Define to 1 if you have the <sys/types.h> header file. */
#define HAVE_SYS_TYPES_H 1

/* Define to 1 if you have the <sys/wait.h> header file. */
#define HAVE_SYS_WAIT_H 1

/* Define to 1 if you have the <time.h> header file. */
#define HAVE_TIME_H 1

/* Define to 1 if you have the <unistd.h> header file. */
#define HAVE_UNISTD_H 1

/* Define to 1 if the system has the type `useconds_t'. */
#define HAVE_USECONDS_T 1

/* Define to 1 if you have the `usleep' function. */
#define HAVE_USLEEP 1

/* I/O restrictions. */
#define IO_RESTRICTIONS_DISABLED 0

/* Don't use libjpeg. */
/* #undef LIBJPEG_MISSING */

/* Don't use libpng. */
/* #undef LIBPNG_MISSING */

/* Don't use libtiff. */
/* #undef LIBTIFF_MISSING */

/* Don't use libz. */
/* #undef LIBZ_MISSING */

/* Unsupported image formats. */
#define MISSING_IMG_FORMATS "-"

/* Inverse hyperbolic functions. */
/* #undef NEED_INVHYP */

/* Don't use OpenEXR. */
/* #undef OPENEXR_MISSING */

/* Name of package */
#define PACKAGE "povray"

/* Define to the address where bug reports for this package should be sent. */
#define PACKAGE_BUGREPORT "unix-bugreports-2011@povray.org"

/* Define to the full name of this package. */
#define PACKAGE_NAME "POV-Ray"

/* Define to the full name and version of this package. */
#define PACKAGE_STRING "POV-Ray 3.8.0-beta.1"

/* Define to the one symbol short name of this package. */
#define PACKAGE_TARNAME "povray"

/* Define to the home page for this package. */
#define PACKAGE_URL ""

/* Define to the version of this package. */
#define PACKAGE_VERSION "3.8.0-beta.1"

/* Compiler version (processed). */
#define POV_COMPILER_INFO "g++ 13 @ x86_64-pc-linux-gnu"

/* Define to necessary symbol if this constant uses a non-standard name on
   your system. */
/* #undef PTHREAD_CREATE_JOINABLE */

/* The size of `float', as computed by sizeof. */
#define SIZEOF_FLOAT 4

/* The size of `int', as computed by sizeof. */
#define SIZEOF_INT 4

/* The size of `long int', as computed by sizeof. */
#define SIZEOF_LONG_INT 8

/* The size of `size_t', as computed by sizeof. */
#define SIZEOF_SIZE_T 8

/* Define to 1 if you have the ANSI C header files. */
#define STDC_HEADERS 1

/* Define to 1 if you can safely include both <sys/time.h> and <time.h>. */
#define TIME_WITH_SYS_TIME 1

/* Define to 1 if your <sys/time.h> declares `struct tm'. */
/* #undef TM_IN_SYS_TIME */

/* Unix-specific debug messages. */
/* #undef UNIX_DEBUG */

/* Use a watch cursor while rendering. */
/* #undef USE_CURSOR */

/* Use the official Boost libraries. */
#define USE_OFFICIAL_BOOST /**/

/* Version number of package */
#define VERSION "3.8.0-beta.1"

/* Base version number of package. */
#define VERSION_BASE "3.8"

/* Define to 1 if the X Window System is missing or not being used. */
/* #undef X_DISPLAY_MISSING */

/* Define to the type of a signed integer type of width exactly 16 bits if
   such a type exists and the standard includes do not define it. */
/* #undef int16_t */

/* Define to the type of a signed integer type of width exactly 32 bits if
   such a type exists and the standard includes do not define it. */
/* #undef int32_t */

/* Define to the type of a signed integer type of width exactly 64 bits if
   such a type exists and the standard includes do not define it. */
/* #undef int64_t */

/* Define to the type of a signed integer type of width exactly 8 bits if such
   a type exists and the standard includes do not define it. */
/* #undef int8_t */

/* Define to `unsigned int' if <sys/types.h> does not define. */
/* #undef size_t */
