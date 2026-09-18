#include <fstream>
#include <algorithm>

// Define your scalars DATA[x][y][z] and dimensions NX, NY and NZ here!

file *DF3FILE;
if((DF3FILE = fopen("MYDF3FILE.df3","wb"))==NULL) return(1);

fputc( (NX >> 8) & 0xFF, DF3FILE);
fputc(  NX       & 0xFF, DF3FILE);

fputc( (NY >> 8) & 0xFF, DF3FILE);
fputc(  NY       & 0xFF, DF3FILE);

fputc( (NZ >> 8) & 0xFF, DF3FILE);
fputc(  NZ       & 0xFF, DF3FILE);

float MAXIMUM=static_cast<float>(DATA[0][0][0]),MINIMUM=static_cast<float>(DATA[0][0][0]);
for (int z=0; z<NZ; z++)
{  for (int y=0; y<NY; y++)
   {  for (int x=0; x<NX; x++)
      {  MAXIMUM=max(static_cast<float>(DATA[x][y][z]),MAXIMUM);
         MINIMUM=min(static_cast<float>(DATA[x][y][z]),MAXIMUM);
      }
   }
}

for (int z=0; z<NZ; z++)
{  for (int y=0; y<NY; y++)
   {  for (int x=0; x<NX; x++)
      {  int VALUE=static_cast<int>(2147483647*(DATA[x][y][z]-MINIMUM)/(MAXIMUM-MINIMUM));

         fputc( (VALUE >> 24) & 0xFF, DF3FILE);
         fputc( (VALUE >> 16) & 0xFF, DF3FILE);
         fputc( (VALUE >>  8) & 0xFF, DF3FILE);
         fputc(  VALUE        & 0xFF, DF3FILE);

      }
   }
}

fclose(DF3FILE);