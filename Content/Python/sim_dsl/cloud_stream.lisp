; BP_CloudStream: moves every actor tagged CloudPuff backward at Speed (cm/s); a puff that is 4 km behind the
; formation respawns 15-30 km ahead (1.5-3.5 km clouds, spread 1.5-6 km to the sides). With ThroughChance it spawns on the formation's track (you fly through it).
(event EventTick (DeltaSeconds)
  (bind pawn (Game|GetPlayerPawn :PlayerIndex 0))
  (bind pl (Transformation|GetActorLocation :self pawn))
  (bind (puffs) (Actor|GetAllActorswithTag :Tag "CloudPuff"))
  (for a puffs
    (Transformation|AddActorWorldOffset :self a :DeltaLocation (Math|Vector|MakeVector :X 0.0 :Y (* (- 0.0 (Variables|Default|GetSpeed)) DeltaSeconds) :Z 0.0) :bSweep false :bTeleport true)
    (if (< (.y (Transformation|GetActorLocation :self a)) (- (.y pl) 600000.0))
      ; latch the random choices (pure nodes re-roll on every use)
      (Variables|Default|SetThr (< (Math|Random|RandomFloat) (Variables|Default|GetThroughChance)))
      (Variables|Default|SetSc (Math|Random|RandomFloatinRange :Min 3000.0 :Max 7000.0))
      (Transformation|SetActorScale3D :self a :NewScale3D (Math|Vector|MakeVector :X (Variables|Default|GetSc) :Y (Variables|Default|GetSc) :Z (Variables|Default|GetSc)))
      (if (Variables|Default|GetThr)
        (Transformation|SetActorLocation :self a :NewLocation (Math|Vector|MakeVector :X (+ (.x pl) (Math|Random|RandomFloatinRange :Min -20000.0 :Max 20000.0)) :Y (+ (.y pl) (Math|Random|RandomFloatinRange :Min 1500000.0 :Max 3000000.0)) :Z (+ (.z pl) (Math|Random|RandomFloatinRange :Min -10000.0 :Max 0.0))) :bSweep false :bTeleport true)
        (else
          (Transformation|SetActorLocation :self a :NewLocation (Math|Vector|MakeVector :X (+ (.x pl) (* (Math|Float|SelectFloat :A 1.0 :B -1.0 :bPickA (< (Math|Random|RandomFloat) 0.5)) (Math|Random|RandomFloatinRange :Min 150000.0 :Max 600000.0))) :Y (+ (.y pl) (Math|Random|RandomFloatinRange :Min 1500000.0 :Max 3000000.0)) :Z (+ (.z pl) (Math|Random|RandomFloatinRange :Min -60000.0 :Max 30000.0))) :bSweep false :bTeleport true))))))
