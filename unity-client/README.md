# Unity client workspace — reserved

This milestone contains no Unity project, generated scene, temporary visual asset, or
playable build. The next client milestone creates the project with a pinned Unity LTS.
Android/iOS are initial targets; platform adapters preserve later PC/console options.

Screen contracts: Splash, Login, Register, Home, Player Profile, Garage, Car Details,
Location Selection, Lobby, Settings. Temporary UI must visibly say "Prototype UI".

Dependency direction: UI → client services → typed API client → FastAPI.
UI never calculates trusted coins, XP, levels or ownership. Use the backend OpenAPI
contract. Store refresh tokens using a vetted Keychain/Keystore adapter, never PlayerPrefs;
serialize refresh requests, keep access tokens in memory, and clear credentials on logout.
Lobby screen is a future unavailable state until real lobby APIs exist. No GPS permission,
physics, checkpoints, driving, rendering pipeline, or multiplayer transport in this milestone.
