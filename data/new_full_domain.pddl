(define (domain full-domain)
   (:requirements :strips :typing)
   (:types
      location locatable - object
      agent item - locatable
      item0 item1 item2 item3 item4 - item
      drone truck - agent
      workshop - location
   )
   (:predicates
      (at_ ?obj - locatable ?loc - location)
      (path ?loc1 - location ?loc2 - location)
      (in ?i - item ?a - agent)
   )
   (:action move
      :parameters ( ?a - agent ?loc1 - location ?loc2 - location)
      :precondition (and (at_ ?a ?loc1) (path ?loc1 ?loc2))
      :effect (and (not (at_ ?a ?loc1)) (at_ ?a ?loc2))
   )
   (:action pick-up
      :parameters ( ?a - agent ?loc - location ?i - item)
      :precondition (and (at_ ?a ?loc) (at_ ?i ?loc))
      :effect (and (not (at_ ?i ?loc)) (in ?i ?a))
   )
   (:action drop
      :parameters ( ?a - agent ?loc - location ?i - item)
      :precondition (and (at_ ?a ?loc) (in ?i ?a))
      :effect (and (not (in ?i ?a)) (at_ ?i ?loc))
   )
   (:action assemble-i3
      :parameters ( ?truck - truck ?workshop - workshop ?i0 - item0 ?i1 - item1 ?i2 - item2 ?i3 - item3)
      :precondition (and (at_ ?truck ?workshop) (at_ ?i0 ?workshop) (at_ ?i1 ?workshop) (at_ ?i2 ?workshop))
      :effect (and (not (at_ ?i0 ?workshop)) (not (at_ ?i1 ?workshop)) (not (at_ ?i2 ?workshop)) (at_ ?i3 ?workshop))
   )
   (:action assemble-i4
      :parameters ( ?workshop - workshop ?i0 - item0 ?i1 - item1 ?i2 - item2 ?i4 - item4 ?truck - truck ?drone - drone)
      :precondition (and (at_ ?truck ?workshop) (at_ ?drone ?workshop) (at_ ?i0 ?workshop) (at_ ?i1 ?workshop) (at_ ?i2 ?workshop))
      :effect (and (not (at_ ?i0 ?workshop)) (not (at_ ?i1 ?workshop)) (not (at_ ?i2 ?workshop)) (at_ ?i4 ?workshop))
   )
)