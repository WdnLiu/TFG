(define (domain mini)
   (:requirements :strips :typing)
   (:types
      thing place - object
      mover load - thing
   )
   (:predicates
      (here ?t - thing ?p - place)
      (link ?p1 - place ?p2 - place)
      (carrying ?l - load ?m - mover)
   )
   (:action go
      :parameters (?m - mover ?from - place ?to - place)
      :precondition (and (here ?m ?from) (link ?from ?to))
      :effect (and (not (here ?m ?from)) (here ?m ?to))
   )
   (:action grab
      :parameters (?m - mover ?p - place ?l - load)
      :precondition (and (here ?m ?p) (here ?l ?p))
      :effect (and (not (here ?l ?p)) (carrying ?l ?m))
   )
   (:action stash
      :parameters (?m - mover ?p - place ?l - load)
      :precondition (and (here ?m ?p) (carrying ?l ?m))
      :effect (and (not (carrying ?l ?m)) (here ?l ?p))
   )
)
