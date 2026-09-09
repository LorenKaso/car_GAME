# Git LFS before large art arrives

Install Git LFS and run `git lfs install` in the eventual checkout. Track selected large
binary formats before adding them, for example:

```sh
git lfs track "*.fbx" "*.blend" "*.psd" "*.tga" "*.wav" "*.mp4"
git add .gitattributes
```

Consider LFS for large PNG/TIFF textures and audio on a per-folder basis. Do not put Unity
.meta, .unity, .prefab or text .asset files into LFS by default. Enable Force Text asset
serialization and Visible Meta Files in Unity. Commit asset .meta files with assets.
Keep build bundles and reproducible city extracts in artifact storage, not Git.
Review GitHub storage/bandwidth costs before uploading large art. No LFS assets exist yet.
