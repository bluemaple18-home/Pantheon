# Gate C G4 wrong-manifest result

`G4_GREEN`。baseline `1 passed in 0.35s`，test-only strengthening 後 target `1 passed in 0.36s`。malformed manifest 得到 `RuntimeManifestError`，tmp_path snapshot 不變，`atomic_write_json` spy 為零，且未建立 coordinator lock。provider/service/network/production mutation 均為 0。
