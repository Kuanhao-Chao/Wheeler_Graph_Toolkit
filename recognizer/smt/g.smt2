; benchmark generated from python API
(set-info :status unknown)
(declare-fun S0 () Int)
(declare-fun S1 () Int)
(declare-fun S11 () Int)
(declare-fun S6 () Int)
(declare-fun S5 () Int)
(declare-fun S2 () Int)
(declare-fun S4 () Int)
(declare-fun S9 () Int)
(declare-fun S8 () Int)
(declare-fun S7 () Int)
(declare-fun S10 () Int)
(declare-fun S3 () Int)
(assert
 (and (> S0 0) (< S0 13)))
(assert
 (and (> S1 0) (< S1 13)))
(assert
 (and (> S11 0) (< S11 13)))
(assert
 (and (> S6 0) (< S6 13)))
(assert
 (and (> S5 0) (< S5 13)))
(assert
 (and (> S2 0) (< S2 13)))
(assert
 (and (> S4 0) (< S4 13)))
(assert
 (and (> S9 0) (< S9 13)))
(assert
 (and (> S8 0) (< S8 13)))
(assert
 (and (> S7 0) (< S7 13)))
(assert
 (and (> S10 0) (< S10 13)))
(assert
 (and (> S3 0) (< S3 13)))
(assert
 (and (distinct S0 S1 S11 S6 S5 S2 S4 S9 S8 S7 S10 S3) true))
(assert
 (<= S0 1))
(assert
 (> S1 S2))
(assert
 (> S1 S3))
(assert
 (< S1 S4))
(assert
 (let (($x171 (<= S1 S5)))
 (=> (< S0 S3) $x171)))
(assert
 (let (($x183 (>= S1 S5)))
 (=> (> S0 S3) $x183)))
(assert
 (< S1 S6))
(assert
 (let (($x171 (<= S1 S5)))
 (=> (< S0 S4) $x171)))
(assert
 (let (($x183 (>= S1 S5)))
 (=> (> S0 S4) $x183)))
(assert
 (< S1 S6))
(assert
 (> S1 S7))
(assert
 (> S1 S8))
(assert
 (let (($x228 (<= S1 S9)))
 (=> (< S0 S7) $x228)))
(assert
 (let (($x240 (>= S1 S9)))
 (=> (> S0 S7) $x240)))
(assert
 (> S1 S10))
(assert
 (< S1 S11))
(assert
 (> S1 S8))
(assert
 (let (($x228 (<= S1 S9)))
 (=> (< S0 S11) $x228)))
(assert
 (let (($x240 (>= S1 S9)))
 (=> (> S0 S11) $x240)))
(assert
 (< S2 S3))
(assert
 (< S2 S4))
(assert
 (< S2 S5))
(assert
 (< S2 S6))
(assert
 (< S2 S5))
(assert
 (< S2 S6))
(assert
 (let (($x301 (<= S2 S7)))
 (let (($x191 (< S1 S6)))
 (=> $x191 $x301))))
(assert
 (=> (> S1 S6) (>= S2 S7)))
(assert
 (< S2 S8))
(assert
 (< S2 S9))
(assert
 (< S2 S10))
(assert
 (< S2 S11))
(assert
 (< S2 S8))
(assert
 (< S2 S9))
(assert
 (< S3 S4))
(assert
 (< S3 S5))
(assert
 (< S3 S6))
(assert
 (< S3 S5))
(assert
 (< S3 S6))
(assert
 (> S3 S7))
(assert
 (let (($x364 (<= S3 S8)))
 (let (($x363 (< S2 S7)))
 (=> $x363 $x364))))
(assert
 (let (($x373 (>= S3 S8)))
 (let (($x372 (> S2 S7)))
 (=> $x372 $x373))))
(assert
 (< S3 S9))
(assert
 (let (($x363 (< S2 S7)))
 (=> $x363 (<= S3 S10))))
(assert
 (let (($x372 (> S2 S7)))
 (=> $x372 (>= S3 S10))))
(assert
 (< S3 S11))
(assert
 (let (($x364 (<= S3 S8)))
 (let (($x327 (< S2 S10)))
 (=> $x327 $x364))))
(assert
 (let (($x373 (>= S3 S8)))
 (=> (> S2 S10) $x373)))
(assert
 (< S3 S9))
(assert
 (> S4 S5))
(assert
 (let (($x415 (<= S4 S6)))
 (let (($x277 (< S2 S3)))
 (=> $x277 $x415))))
(assert
 (let (($x421 (>= S4 S6)))
 (=> (> S2 S3) $x421)))
(assert
 (> S4 S5))
(assert
 (let (($x415 (<= S4 S6)))
 (let (($x289 (< S2 S5)))
 (=> $x289 $x415))))
(assert
 (let (($x421 (>= S4 S6)))
 (=> (> S2 S5) $x421)))
(assert
 (> S4 S7))
(assert
 (> S4 S8))
(assert
 (> S4 S9))
(assert
 (> S4 S10))
(assert
 (let (($x462 (<= S4 S11)))
 (let (($x315 (< S2 S8)))
 (=> $x315 $x462))))
(assert
 (=> (> S2 S8) (>= S4 S11)))
(assert
 (> S4 S8))
(assert
 (> S4 S9))
(assert
 (< S5 S6))
(assert
 (let (($x339 (< S3 S4)))
 (=> $x339 (<= S5 S5))))
(assert
 (=> (> S3 S4) (>= S5 S5)))
(assert
 (< S5 S6))
(assert
 (> S5 S7))
(assert
 (> S5 S8))
(assert
 (let (($x504 (<= S5 S9)))
 (=> (< S3 S7) $x504)))
(assert
 (let (($x513 (>= S5 S9)))
 (let (($x357 (> S3 S7)))
 (=> $x357 $x513))))
(assert
 (> S5 S10))
(assert
 (< S5 S11))
(assert
 (> S5 S8))
(assert
 (let (($x504 (<= S5 S9)))
 (let (($x394 (< S3 S11)))
 (=> $x394 $x504))))
(assert
 (let (($x513 (>= S5 S9)))
 (=> (> S3 S11) $x513)))
(assert
 (> S6 S5))
(assert
 (let (($x345 (< S3 S5)))
 (=> $x345 (<= S6 S6))))
(assert
 (=> (> S3 S5) (>= S6 S6)))
(assert
 (> S6 S7))
(assert
 (> S6 S8))
(assert
 (> S6 S9))
(assert
 (> S6 S10))
(assert
 (let (($x573 (<= S6 S11)))
 (=> (< S3 S8) $x573)))
(assert
 (let (($x582 (>= S6 S11)))
 (=> (> S3 S8) $x582)))
(assert
 (> S6 S8))
(assert
 (> S6 S9))
(assert
 (< S5 S6))
(assert
 (> S5 S7))
(assert
 (> S5 S8))
(assert
 (let (($x504 (<= S5 S9)))
 (=> (< S4 S7) $x504)))
(assert
 (let (($x513 (>= S5 S9)))
 (let (($x438 (> S4 S7)))
 (=> $x438 $x513))))
(assert
 (> S5 S10))
(assert
 (< S5 S11))
(assert
 (> S5 S8))
(assert
 (let (($x504 (<= S5 S9)))
 (=> (< S4 S11) $x504)))
(assert
 (let (($x513 (>= S5 S9)))
 (=> (> S4 S11) $x513)))
(assert
 (> S6 S7))
(assert
 (> S6 S8))
(assert
 (> S6 S9))
(assert
 (> S6 S10))
(assert
 (let (($x573 (<= S6 S11)))
 (=> (< S5 S8) $x573)))
(assert
 (let (($x582 (>= S6 S11)))
 (let (($x497 (> S5 S8)))
 (=> $x497 $x582))))
(assert
 (> S6 S8))
(assert
 (> S6 S9))
(assert
 (< S7 S8))
(assert
 (< S7 S9))
(assert
 (< S7 S10))
(assert
 (< S7 S11))
(assert
 (< S7 S8))
(assert
 (< S7 S9))
(assert
 (< S8 S9))
(assert
 (=> (< S7 S7) (<= S8 S10)))
(assert
 (=> (> S7 S7) (>= S8 S10)))
(assert
 (< S8 S11))
(assert
 (let (($x629 (< S7 S10)))
 (=> $x629 (<= S8 S8))))
(assert
 (let (($x663 (> S7 S10)))
 (=> $x663 (>= S8 S8))))
(assert
 (< S8 S9))
(assert
 (> S9 S10))
(assert
 (< S9 S11))
(assert
 (> S9 S8))
(assert
 (let (($x635 (< S7 S11)))
 (=> $x635 (<= S9 S9))))
(assert
 (=> (> S7 S11) (>= S9 S9)))
(assert
 (< S10 S11))
(assert
 (let (($x629 (< S7 S10)))
 (=> $x629 (<= S10 S8))))
(assert
 (let (($x663 (> S7 S10)))
 (=> $x663 (>= S10 S8))))
(assert
 (< S10 S9))
(assert
 (> S11 S8))
(assert
 (> S11 S9))
(assert
 (< S8 S9))
(check-sat)
