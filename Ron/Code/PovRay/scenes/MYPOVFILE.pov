#declare NX = 64;                                     // x-dimension
#declare NY = 64;                                     // y-dimension
#declare NZ = 64;                                     // z-dimension
#declare DIAG = <NX,NY,NZ>;

global_settings
{  ambient_light <1,1,1>
   assumed_gamma 1
}
camera
{  location <0,-7/4*NY,2/3*NZ>
   up z
   right x                                            // default: 4/3*x
   sky <0,0,1>
   look_at <0,0,0>
}
light_source
{  <2*NX,-NY,2*NZ>
   color rgb <1,1,1>
   media_interaction on
   media_attenuation on
   shadowless
}

//-------------------------------------------------------------------------------------------------

#declare DENS = interior
                {  media
                   {  intervals 100                   // number of ray-intervals
                      ratio 0.5
                      samples 3,3                     // maximum,minimum of samples per voxel
                      method 3                        // 1, 2 or 3 (3 requires samples 3,3)
                      emission 3*<1,1,1>/100
                      absorption <1,1,1>/1000
                      scattering { 1, <0,0,0> }
                      confidence 0.999                // default: 0.9
                      variance 1/10000                // default: 1/128
                      density
                      {  density_file df3 "MYDF3FILE.df3"
                         interpolate 1
                         color_map                    // colour map with (smooth) linear transition(s)
                         {  [0.014 rgb <0.0,0.0,0.0>]  // 0.0 ~ 'black'
                            [0.088 rgb <1.0,0.0,0.0>]
                            [0.188 rgb <1.0,0.6,0.0>]
                            [0.196 rgb <1.0,1.0,0.0>]
                            [0.216 rgb <1.0,1.0,1.0>]  // 1.0 ~ 'white'
                         }
                      }
                   }
                }

box
{  <0,0,0>, <1,1,1>
   pigment { rgbt <0,0,0,1> }
   hollow
   interior { DENS }
   scale DIAG
   translate -DIAG/2
   //rotate <90,0,0>
   //rotate <0,0,360*clock>                           // rotation around z-axis
}

//-------------------------------------------------------------------------------------------------

#declare RADIUS = 0.2;
#declare FRAME = texture
                 {  pigment { rgb <0.5,0.5,0.5> }
                 }
union
{  sphere { <00,00,00>, RADIUS texture { FRAME } }
   sphere { <NX,00,00>, RADIUS texture { FRAME } }
   sphere { <NX,NY,00>, RADIUS texture { FRAME } }
   sphere { <00,NY,00>, RADIUS texture { FRAME } }
   sphere { <00,00,NZ>, RADIUS texture { FRAME } }
   sphere { <NX,00,NZ>, RADIUS texture { FRAME } }
   sphere { <NX,NY,NZ>, RADIUS texture { FRAME } }
   sphere { <00,NY,NZ>, RADIUS texture { FRAME } }
   translate -DIAG/2
   //rotate <0,0,360*clock>                           // rotation around z-axis
}
union
{  cylinder { <00,00,00>, <NX,00,00>, RADIUS texture { FRAME } }
   cylinder { <NX,00,00>, <NX,NY,00>, RADIUS texture { FRAME } }
   cylinder { <NX,NY,00>, <00,NY,00>, RADIUS texture { FRAME } }
   cylinder { <00,NY,00>, <00,00,00>, RADIUS texture { FRAME } }
   cylinder { <00,00,00>, <00,00,NZ>, RADIUS texture { FRAME } }
   cylinder { <NX,00,00>, <NX,00,NZ>, RADIUS texture { FRAME } }
   cylinder { <NX,NY,00>, <NX,NY,NZ>, RADIUS texture { FRAME } }
   cylinder { <00,NY,00>, <00,NY,NZ>, RADIUS texture { FRAME } }
   cylinder { <00,00,NZ>, <NX,00,NZ>, RADIUS texture { FRAME } }
   cylinder { <NX,00,NZ>, <NX,NY,NZ>, RADIUS texture { FRAME } }
   cylinder { <NX,NY,NZ>, <00,NY,NZ>, RADIUS texture { FRAME } }
   cylinder { <00,NY,NZ>, <00,00,NZ>, RADIUS texture { FRAME } }
   translate -DIAG/2
   //rotate <0,0,360*clock>                           // rotation around z-axis
}