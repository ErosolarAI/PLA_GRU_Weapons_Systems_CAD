; CNC Program for Fin_Assembly_3
; Material: Titanium_Alloy
; Machine: DMG MORI NTX 1000 5-axis
; Programmer: PLA Engineering
; Date: 2025-12-15

G21 G40 G49 G80 G90 G94
G28 G91 Z0
G28 G91 X0 Y0

; Tool definitions
T1 M6 ; 20mm Face Mill
G43 H1 Z100
S8000 M3
G54

; Roughing operations
G0 X0 Y0 Z10
G1 Z-5 F1000
; ... machining operations ...

; Finishing operations
T2 M6 ; 10mm Ball Nose
G43 H2 Z100
S12000 M3
; ... finishing operations ...

; Drilling/tapping
T3 M6 ; 8mm Drill
G43 H3 Z100
S5000 M3
; ... hole patterns ...

G28 G91 Z0
G28 G91 X0 Y0
M30
