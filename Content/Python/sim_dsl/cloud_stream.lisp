; BP_CloudStream: moves every actor tagged CloudPuff backward at Speed (cm/s); a puff that is 4 km behind the
; formation respawns 12-18 km ahead. With ThroughChance it spawns on the formation's track (you fly through it).
(event EventTick (DeltaSeconds)
  (bind pawn (Game|GetPlayerPawn :PlayerIndex 0))
  (bind pl (Transformation|GetActorLocation :self pawn))
  (bind (puffs) (Actor|GetAllActorswithTag :Tag "CloudPuff"))
  (for a puffs
    (Transformation|AddActorWorldOffset :self a :DeltaLocation (Math|Vector|MakeVector :X 0.0 :Y (* (- 0.0 (Variables|Default|GetSpeed)) DeltaSeconds) :Z 0.0) :bSweep false :bTeleport true)
    (if (< (.y (Transformation|GetActorLocation :self a)) (- (.y pl) 400000.0))
      ; latch the random choices (pure nodes re-roll on every use)
      (Variables|Default|SetThr (< (Math|Random|RandomFloat) (Variables|Default|GetThroughChance)))
      (Variables|Default|SetSc (Math|Random|RandomFloatinRange :Min 250.0 :Max 700.0))
      (Transformation|SetActorScale3D :self a :NewScale3D (Math|Vector|MakeVector :X (Variables|Default|GetSc) :Y (Variables|Default|GetSc) :Z (* (Variables|Default|GetSc) 0.75)))
      (if (Variables|Default|GetThr)
        (Transformation|SetActorLocation :self a :NewLocation (Math|Vector|MakeVector :X (+ (.x pl) (Math|Random|RandomFloatinRange :Min -4000.0 :Max 4000.0)) :Y (+ (.y pl) (Math|Random|RandomFloatinRange :Min 1200000.0 :Max 1800000.0)) :Z (+ (.z pl) (Math|Random|RandomFloatinRange :Min -3000.0 :Max 3000.0))) :bSweep false :bTeleport true)
        (else
          (Transformation|SetActorLocation :self a :NewLocation (Math|Vector|MakeVector :X (+ (.x pl) (Math|Random|RandomFloatinRange :Min -80000.0 :Max 80000.0)) :Y (+ (.y pl) (Math|Random|RandomFloatinRange :Min 1200000.0 :Max 1800000.0)) :Z (+ (.z pl) (Math|Random|RandomFloatinRange :Min -25000.0 :Max 25000.0))) :bSweep false :bTeleport true))))))
