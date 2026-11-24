"""Periksa secara statis bahwa SETIAP endpoint di semua layanan punya aturan akses.

Membaca services/*/main.py (tanpa menjalankannya), mencari dekorator @app.get/post/patch/...
dan memastikan masing-masing memakai auth.dibutuhkan(...), baik lewat `dependencies=[...]`
maupun parameter `Depends(...)`. Hanya endpoint pada daftar PUBLIK yang boleh tanpa token.

Pemakaian:  python scripts/cek_proteksi_route.py
"""
import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent / "services"
METODE = {"get", "post", "put", "patch", "delete"}

# (layanan, metode, path) yang sengaja terbuka.
PUBLIK = {
    ("auth", "POST", "/auth/login"),      # pintu masuk: tidak mungkin butuh token
}
SEHAT = "/health"                          # pemeriksaan kesehatan untuk Docker, tanpa data


def memakai_auth(node) -> bool:
    return any(
        isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "dibutuhkan"
        for n in ast.walk(node)
    )


def periksa(layanan: str, berkas: pathlib.Path):
    pohon = ast.parse(berkas.read_text(encoding="utf-8"))
    hasil = []
    for fn in ast.walk(pohon):
        if not isinstance(fn, ast.FunctionDef):
            continue
        for dek in fn.decorator_list:
            if not (isinstance(dek, ast.Call) and isinstance(dek.func, ast.Attribute)
                    and isinstance(dek.func.value, ast.Name) and dek.func.value.id == "app"
                    and dek.func.attr in METODE and dek.args):
                continue
            path = ast.literal_eval(dek.args[0])
            metode = dek.func.attr.upper()
            lewat_dekorator = any(k.arg == "dependencies" and memakai_auth(k.value) for k in dek.keywords)
            lewat_parameter = any(memakai_auth(d) for d in fn.args.defaults + fn.args.kw_defaults if d is not None)
            terlindungi = lewat_dekorator or lewat_parameter
            publik = (layanan, metode, path) in PUBLIK or (metode == "GET" and path == SEHAT)
            hasil.append((metode, path, fn.name, terlindungi, publik))
    return hasil


gagal = []
total = 0
for dir_layanan in sorted(p for p in ROOT.iterdir() if (p / "main.py").exists()):
    for metode, path, fungsi, terlindungi, publik in periksa(dir_layanan.name, dir_layanan / "main.py"):
        total += 1
        status = "terlindungi" if terlindungi else ("PUBLIK (diizinkan)" if publik else "TANPA PROTEKSI")
        print(f"{dir_layanan.name:11s} {metode:6s} {path:32s} {status}")
        if not terlindungi and not publik:
            gagal.append(f"{dir_layanan.name} {metode} {path} ({fungsi})")

print()
if gagal:
    print("GAGAL: endpoint tanpa aturan akses:")
    for g in gagal:
        print("  -", g)
    sys.exit(1)
print(f"ok   : {total} endpoint diperiksa, semuanya punya aturan akses atau memang publik")
