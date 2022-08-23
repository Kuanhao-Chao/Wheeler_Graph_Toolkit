; benchmark generated from python API
(set-info :status unknown)
(declare-fun S0 () Int)
(declare-fun S1 () Int)
(declare-fun S6 () Int)
(declare-fun S5 () Int)
(declare-fun S2 () Int)
(declare-fun S4 () Int)
(declare-fun S7 () Int)
(declare-fun S3 () Int)
(assert
 (and (> S0 0) (< S0 9)))
(assert
 (and (> S1 0) (< S1 9)))
(assert
 (and (> S6 0) (< S6 9)))
(assert
 (and (> S5 0) (< S5 9)))
(assert
 (and (> S2 0) (< S2 9)))
(assert
 (and (> S4 0) (< S4 9)))
(assert
 (and (> S7 0) (< S7 9)))
(assert
 (and (> S3 0) (< S3 9)))
(assert
 (and (distinct S0 S1 S6 S5 S2 S4 S7 S3) true))
(assert
 (<= S0 1))
(assert
 (let (($x108 (< S1 S2)))
 (=> true $x108)))
(assert
 (let (($x119 (<= S1 S2)))
 (let (($x118 (and false (< S0 S1))))
 (=> $x118 $x119))))
(assert
 (let (($x127 (< S1 S3)))
 (=> true $x127)))
(assert
 (let (($x135 (<= S1 S3)))
 (let (($x118 (and false (< S0 S1))))
 (=> $x118 $x135))))
(assert
 (let (($x137 (< S1 S4)))
 (=> true $x137)))
(assert
 (let (($x145 (<= S1 S4)))
 (let (($x118 (and false (< S0 S1))))
 (=> $x118 $x145))))
(assert
 (=> false (< S1 S5)))
(assert
 (let (($x157 (<= S1 S5)))
 (=> (and true (< S0 S2)) $x157)))
(assert
 (let (($x166 (< S1 S6)))
 (=> true $x166)))
(assert
 (let (($x175 (<= S1 S6)))
 (=> (and false (< S0 S2)) $x175)))
(assert
 (let (($x177 (< S1 S7)))
 (=> true $x177)))
(assert
 (let (($x187 (<= S1 S7)))
 (=> (and false (< S0 S3)) $x187)))
(assert
 (let (($x108 (< S1 S2)))
 (=> true $x108)))
(assert
 (let (($x119 (<= S1 S2)))
 (=> (and false (< S0 S4)) $x119)))
(assert
 (let (($x127 (< S1 S3)))
 (=> true $x127)))
(assert
 (let (($x135 (<= S1 S3)))
 (=> (and false (< S0 S6)) $x135)))
(assert
 (=> false (< S1 S5)))
(assert
 (let (($x157 (<= S1 S5)))
 (=> (and true (< S0 S7)) $x157)))
(assert
 (let (($x221 (< S2 S1)))
 (=> false $x221)))
(assert
 (let (($x110 (<= S2 S1)))
 (let (($x226 (and false (< S1 S0))))
 (=> $x226 $x110))))
(assert
 (let (($x232 (< S2 S3)))
 (=> false $x232)))
(assert
 (let (($x241 (<= S2 S3)))
 (let (($x240 (and true (< S1 S1))))
 (=> $x240 $x241))))
(assert
 (let (($x245 (< S2 S4)))
 (=> false $x245)))
(assert
 (let (($x252 (<= S2 S4)))
 (let (($x240 (and true (< S1 S1))))
 (=> $x240 $x252))))
(assert
 (=> false (< S2 S5)))
(assert
 (let (($x262 (<= S2 S5)))
 (let (($x108 (< S1 S2)))
 (let (($x261 (and false $x108)))
 (=> $x261 $x262)))))
(assert
 (let (($x264 (< S2 S6)))
 (=> true $x264)))
(assert
 (let (($x271 (<= S2 S6)))
 (let (($x108 (< S1 S2)))
 (let (($x261 (and false $x108)))
 (=> $x261 $x271)))))
(assert
 (let (($x273 (< S2 S7)))
 (=> true $x273)))
(assert
 (let (($x281 (<= S2 S7)))
 (let (($x127 (< S1 S3)))
 (let (($x280 (and false $x127)))
 (=> $x280 $x281)))))
(assert
 (let (($x283 (< S2 S2)))
 (=> false $x283)))
(assert
 (let (($x285 (<= S2 S2)))
 (let (($x137 (< S1 S4)))
 (let (($x287 (and true $x137)))
 (=> $x287 $x285)))))
(assert
 (let (($x232 (< S2 S3)))
 (=> false $x232)))
(assert
 (let (($x241 (<= S2 S3)))
 (let (($x166 (< S1 S6)))
 (let (($x289 (and true $x166)))
 (=> $x289 $x241)))))
(assert
 (=> false (< S2 S5)))
(assert
 (let (($x262 (<= S2 S5)))
 (let (($x177 (< S1 S7)))
 (let (($x293 (and false $x177)))
 (=> $x293 $x262)))))
(assert
 (let (($x296 (< S3 S1)))
 (=> false $x296)))
(assert
 (let (($x129 (<= S3 S1)))
 (let (($x226 (and false (< S1 S0))))
 (=> $x226 $x129))))
(assert
 (let (($x301 (< S3 S2)))
 (=> false $x301)))
(assert
 (let (($x234 (<= S3 S2)))
 (let (($x240 (and true (< S1 S1))))
 (=> $x240 $x234))))
(assert
 (let (($x306 (< S3 S4)))
 (=> false $x306)))
(assert
 (let (($x313 (<= S3 S4)))
 (let (($x240 (and true (< S1 S1))))
 (=> $x240 $x313))))
(assert
 (=> false (< S3 S5)))
(assert
 (let (($x322 (<= S3 S5)))
 (let (($x108 (< S1 S2)))
 (let (($x261 (and false $x108)))
 (=> $x261 $x322)))))
(assert
 (let (($x324 (< S3 S6)))
 (=> true $x324)))
(assert
 (let (($x331 (<= S3 S6)))
 (let (($x108 (< S1 S2)))
 (let (($x261 (and false $x108)))
 (=> $x261 $x331)))))
(assert
 (let (($x333 (< S3 S7)))
 (=> true $x333)))
(assert
 (let (($x340 (<= S3 S7)))
 (let (($x127 (< S1 S3)))
 (let (($x280 (and false $x127)))
 (=> $x280 $x340)))))
(assert
 (let (($x301 (< S3 S2)))
 (=> false $x301)))
(assert
 (let (($x234 (<= S3 S2)))
 (let (($x137 (< S1 S4)))
 (let (($x287 (and true $x137)))
 (=> $x287 $x234)))))
(assert
 (=> false (< S3 S3)))
(assert
 (let (($x346 (<= S3 S3)))
 (let (($x166 (< S1 S6)))
 (let (($x289 (and true $x166)))
 (=> $x289 $x346)))))
(assert
 (=> false (< S3 S5)))
(assert
 (let (($x322 (<= S3 S5)))
 (let (($x177 (< S1 S7)))
 (let (($x293 (and false $x177)))
 (=> $x293 $x322)))))
(assert
 (let (($x351 (< S4 S1)))
 (=> false $x351)))
(assert
 (let (($x139 (<= S4 S1)))
 (let (($x226 (and false (< S1 S0))))
 (=> $x226 $x139))))
(assert
 (let (($x357 (< S4 S2)))
 (=> false $x357)))
(assert
 (let (($x247 (<= S4 S2)))
 (let (($x240 (and true (< S1 S1))))
 (=> $x240 $x247))))
(assert
 (let (($x363 (< S4 S3)))
 (=> false $x363)))
(assert
 (let (($x308 (<= S4 S3)))
 (let (($x240 (and true (< S1 S1))))
 (=> $x240 $x308))))
(assert
 (=> false (< S4 S5)))
(assert
 (let (($x376 (<= S4 S5)))
 (let (($x108 (< S1 S2)))
 (let (($x261 (and false $x108)))
 (=> $x261 $x376)))))
(assert
 (let (($x378 (< S4 S6)))
 (=> true $x378)))
(assert
 (let (($x385 (<= S4 S6)))
 (let (($x108 (< S1 S2)))
 (let (($x261 (and false $x108)))
 (=> $x261 $x385)))))
(assert
 (let (($x387 (< S4 S7)))
 (=> true $x387)))
(assert
 (let (($x394 (<= S4 S7)))
 (let (($x127 (< S1 S3)))
 (let (($x280 (and false $x127)))
 (=> $x280 $x394)))))
(assert
 (let (($x357 (< S4 S2)))
 (=> false $x357)))
(assert
 (let (($x247 (<= S4 S2)))
 (let (($x137 (< S1 S4)))
 (let (($x287 (and true $x137)))
 (=> $x287 $x247)))))
(assert
 (let (($x363 (< S4 S3)))
 (=> false $x363)))
(assert
 (let (($x308 (<= S4 S3)))
 (let (($x166 (< S1 S6)))
 (let (($x289 (and true $x166)))
 (=> $x289 $x308)))))
(assert
 (=> false (< S4 S5)))
(assert
 (let (($x376 (<= S4 S5)))
 (let (($x177 (< S1 S7)))
 (let (($x293 (and false $x177)))
 (=> $x293 $x376)))))
(assert
 (=> false (< S5 S1)))
(assert
 (let (($x149 (<= S5 S1)))
 (=> (and true (< S2 S0)) $x149)))
(assert
 (=> true (< S5 S2)))
(assert
 (let (($x256 (<= S5 S2)))
 (let (($x221 (< S2 S1)))
 (let (($x418 (and false $x221)))
 (=> $x418 $x256)))))
(assert
 (=> true (< S5 S3)))
(assert
 (let (($x317 (<= S5 S3)))
 (let (($x221 (< S2 S1)))
 (let (($x418 (and false $x221)))
 (=> $x418 $x317)))))
(assert
 (=> true (< S5 S4)))
(assert
 (let (($x371 (<= S5 S4)))
 (let (($x221 (< S2 S1)))
 (let (($x418 (and false $x221)))
 (=> $x418 $x371)))))
(assert
 (=> true (< S5 S6)))
(assert
 (let (($x438 (<= S5 S6)))
 (let (($x283 (< S2 S2)))
 (let (($x437 (and false $x283)))
 (=> $x437 $x438)))))
(assert
 (=> true (< S5 S7)))
(assert
 (let (($x448 (<= S5 S7)))
 (=> (and false (< S2 S3)) $x448)))
(assert
 (=> true (< S5 S2)))
(assert
 (let (($x256 (<= S5 S2)))
 (let (($x245 (< S2 S4)))
 (let (($x450 (and false $x245)))
 (=> $x450 $x256)))))
(assert
 (=> true (< S5 S3)))
(assert
 (let (($x317 (<= S5 S3)))
 (let (($x264 (< S2 S6)))
 (let (($x452 (and false $x264)))
 (=> $x452 $x317)))))
(assert
 (=> false (< S5 S5)))
(assert
 (let (($x456 (<= S5 S5)))
 (=> (and true (< S2 S7)) $x456)))
(assert
 (let (($x460 (< S6 S1)))
 (=> false $x460)))
(assert
 (let (($x168 (<= S6 S1)))
 (=> (and false (< S2 S0)) $x168)))
(assert
 (let (($x467 (< S6 S2)))
 (=> false $x467)))
(assert
 (let (($x266 (<= S6 S2)))
 (let (($x221 (< S2 S1)))
 (let (($x418 (and false $x221)))
 (=> $x418 $x266)))))
(assert
 (let (($x473 (< S6 S3)))
 (=> false $x473)))
(assert
 (let (($x326 (<= S6 S3)))
 (let (($x221 (< S2 S1)))
 (let (($x418 (and false $x221)))
 (=> $x418 $x326)))))
(assert
 (let (($x479 (< S6 S4)))
 (=> false $x479)))
(assert
 (let (($x380 (<= S6 S4)))
 (let (($x221 (< S2 S1)))
 (let (($x418 (and false $x221)))
 (=> $x418 $x380)))))
(assert
 (=> false (< S6 S5)))
(assert
 (let (($x432 (<= S6 S5)))
 (let (($x283 (< S2 S2)))
 (let (($x437 (and false $x283)))
 (=> $x437 $x432)))))
(assert
 (let (($x491 (< S6 S7)))
 (=> false $x491)))
(assert
 (let (($x499 (<= S6 S7)))
 (=> (and true (< S2 S3)) $x499)))
(assert
 (let (($x467 (< S6 S2)))
 (=> false $x467)))
(assert
 (let (($x266 (<= S6 S2)))
 (let (($x245 (< S2 S4)))
 (let (($x450 (and false $x245)))
 (=> $x450 $x266)))))
(assert
 (let (($x473 (< S6 S3)))
 (=> false $x473)))
(assert
 (let (($x326 (<= S6 S3)))
 (let (($x264 (< S2 S6)))
 (let (($x452 (and false $x264)))
 (=> $x452 $x326)))))
(assert
 (=> false (< S6 S5)))
(assert
 (let (($x432 (<= S6 S5)))
 (=> (and false (< S2 S7)) $x432)))
(assert
 (let (($x507 (< S7 S1)))
 (=> false $x507)))
(assert
 (let (($x179 (<= S7 S1)))
 (=> (and false (< S3 S0)) $x179)))
(assert
 (let (($x519 (< S7 S2)))
 (=> false $x519)))
(assert
 (let (($x275 (<= S7 S2)))
 (let (($x296 (< S3 S1)))
 (let (($x524 (and false $x296)))
 (=> $x524 $x275)))))
(assert
 (let (($x526 (< S7 S3)))
 (=> false $x526)))
(assert
 (let (($x335 (<= S7 S3)))
 (let (($x296 (< S3 S1)))
 (let (($x524 (and false $x296)))
 (=> $x524 $x335)))))
(assert
 (let (($x532 (< S7 S4)))
 (=> false $x532)))
(assert
 (let (($x389 (<= S7 S4)))
 (let (($x296 (< S3 S1)))
 (let (($x524 (and false $x296)))
 (=> $x524 $x389)))))
(assert
 (=> false (< S7 S5)))
(assert
 (let (($x442 (<= S7 S5)))
 (=> (and false (< S3 S2)) $x442)))
(assert
 (let (($x545 (< S7 S6)))
 (=> false $x545)))
(assert
 (let (($x493 (<= S7 S6)))
 (=> (and true (< S3 S2)) $x493)))
(assert
 (let (($x519 (< S7 S2)))
 (=> false $x519)))
(assert
 (let (($x275 (<= S7 S2)))
 (=> (and false (< S3 S4)) $x275)))
(assert
 (let (($x526 (< S7 S3)))
 (=> false $x526)))
(assert
 (let (($x335 (<= S7 S3)))
 (=> (and false (< S3 S6)) $x335)))
(assert
 (=> false (< S7 S5)))
(assert
 (let (($x442 (<= S7 S5)))
 (=> (and false (< S3 S7)) $x442)))
(assert
 (let (($x221 (< S2 S1)))
 (=> false $x221)))
(assert
 (let (($x110 (<= S2 S1)))
 (=> (and false (< S4 S0)) $x110)))
(assert
 (let (($x283 (< S2 S2)))
 (=> false $x283)))
(assert
 (let (($x285 (<= S2 S2)))
 (let (($x351 (< S4 S1)))
 (let (($x565 (and true $x351)))
 (=> $x565 $x285)))))
(assert
 (let (($x232 (< S2 S3)))
 (=> false $x232)))
(assert
 (let (($x241 (<= S2 S3)))
 (let (($x351 (< S4 S1)))
 (let (($x565 (and true $x351)))
 (=> $x565 $x241)))))
(assert
 (let (($x245 (< S2 S4)))
 (=> false $x245)))
(assert
 (let (($x252 (<= S2 S4)))
 (let (($x351 (< S4 S1)))
 (let (($x565 (and true $x351)))
 (=> $x565 $x252)))))
(assert
 (=> false (< S2 S5)))
(assert
 (let (($x262 (<= S2 S5)))
 (let (($x357 (< S4 S2)))
 (let (($x571 (and false $x357)))
 (=> $x571 $x262)))))
(assert
 (let (($x264 (< S2 S6)))
 (=> true $x264)))
(assert
 (let (($x271 (<= S2 S6)))
 (let (($x357 (< S4 S2)))
 (let (($x571 (and false $x357)))
 (=> $x571 $x271)))))
(assert
 (let (($x273 (< S2 S7)))
 (=> true $x273)))
(assert
 (let (($x281 (<= S2 S7)))
 (=> (and false (< S4 S3)) $x281)))
(assert
 (let (($x232 (< S2 S3)))
 (=> false $x232)))
(assert
 (let (($x241 (<= S2 S3)))
 (=> (and true (< S4 S6)) $x241)))
(assert
 (=> false (< S2 S5)))
(assert
 (let (($x262 (<= S2 S5)))
 (=> (and false (< S4 S7)) $x262)))
(assert
 (let (($x296 (< S3 S1)))
 (=> false $x296)))
(assert
 (let (($x129 (<= S3 S1)))
 (=> (and false (< S6 S0)) $x129)))
(assert
 (let (($x301 (< S3 S2)))
 (=> false $x301)))
(assert
 (let (($x234 (<= S3 S2)))
 (let (($x460 (< S6 S1)))
 (let (($x588 (and true $x460)))
 (=> $x588 $x234)))))
(assert
 (=> false (< S3 S3)))
(assert
 (let (($x346 (<= S3 S3)))
 (let (($x460 (< S6 S1)))
 (let (($x588 (and true $x460)))
 (=> $x588 $x346)))))
(assert
 (let (($x306 (< S3 S4)))
 (=> false $x306)))
(assert
 (let (($x313 (<= S3 S4)))
 (let (($x460 (< S6 S1)))
 (let (($x588 (and true $x460)))
 (=> $x588 $x313)))))
(assert
 (=> false (< S3 S5)))
(assert
 (let (($x322 (<= S3 S5)))
 (let (($x467 (< S6 S2)))
 (let (($x594 (and false $x467)))
 (=> $x594 $x322)))))
(assert
 (let (($x324 (< S3 S6)))
 (=> true $x324)))
(assert
 (let (($x331 (<= S3 S6)))
 (let (($x467 (< S6 S2)))
 (let (($x594 (and false $x467)))
 (=> $x594 $x331)))))
(assert
 (let (($x333 (< S3 S7)))
 (=> true $x333)))
(assert
 (let (($x340 (<= S3 S7)))
 (=> (and false (< S6 S3)) $x340)))
(assert
 (let (($x301 (< S3 S2)))
 (=> false $x301)))
(assert
 (let (($x234 (<= S3 S2)))
 (=> (and true (< S6 S4)) $x234)))
(assert
 (=> false (< S3 S5)))
(assert
 (let (($x322 (<= S3 S5)))
 (=> (and false (< S6 S7)) $x322)))
(assert
 (=> false (< S5 S1)))
(assert
 (let (($x149 (<= S5 S1)))
 (=> (and true (< S7 S0)) $x149)))
(assert
 (=> true (< S5 S2)))
(assert
 (let (($x256 (<= S5 S2)))
 (let (($x507 (< S7 S1)))
 (let (($x612 (and false $x507)))
 (=> $x612 $x256)))))
(assert
 (=> true (< S5 S3)))
(assert
 (let (($x317 (<= S5 S3)))
 (let (($x507 (< S7 S1)))
 (let (($x612 (and false $x507)))
 (=> $x612 $x317)))))
(assert
 (=> true (< S5 S4)))
(assert
 (let (($x371 (<= S5 S4)))
 (let (($x507 (< S7 S1)))
 (let (($x612 (and false $x507)))
 (=> $x612 $x371)))))
(assert
 (=> false (< S5 S5)))
(assert
 (let (($x456 (<= S5 S5)))
 (=> (and true (< S7 S2)) $x456)))
(assert
 (=> true (< S5 S6)))
(assert
 (let (($x438 (<= S5 S6)))
 (=> (and false (< S7 S2)) $x438)))
(assert
 (=> true (< S5 S7)))
(assert
 (let (($x448 (<= S5 S7)))
 (=> (and false (< S7 S3)) $x448)))
(assert
 (=> true (< S5 S2)))
(assert
 (let (($x256 (<= S5 S2)))
 (=> (and false (< S7 S4)) $x256)))
(assert
 (=> true (< S5 S3)))
(assert
 (let (($x317 (<= S5 S3)))
 (=> (and false (< S7 S6)) $x317)))
(check-sat)
