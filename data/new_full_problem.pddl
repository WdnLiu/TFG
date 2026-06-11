(define (problem full-problem)
 (:domain full-domain)
 (:objects
   b c d e g - location
   a f - workshop
   i0 i02 - item0
   i1 i12 - item1
   i2 i22 - item2
   i3 - item3
   i4 - item4
   drone1 - drone
   truck1 truck2 - truck
 )
 (:init (at_ truck1 b) (at_ truck2 e) (at_ drone1 e) (at_ i0 b) (at_ i1 b) (at_ i2 d) (at_ i02 g) (at_ i12 f) (at_ i22 e) (path a e) (path e a) (path a b) (path b a) (path b c) (path c b) (path c d) (path d c) (path a d) (path d a) (path e g) (path g e) (path e f) (path f e))
 (:goal (and (at_ i3 g) (at_ i4 c)))
)
