(define (problem mini-task)
  (:domain mini)
  (:objects
    a b c - place
    m1 - mover
    x1 - load
  )
  (:init
    (here m1 a)
    (here x1 b)
    (link a b)
    (link b a)
    (link b c)
    (link c b)
  )
  (:goal (and
    (here x1 c)
  ))
)
