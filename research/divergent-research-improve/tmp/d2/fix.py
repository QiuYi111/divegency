import pathlib
p = pathlib.Path("/Users/jingyi/divegency/research/divergent-research-improve/tracks/D2.md")
t = p.read_text(encoding="utf-8")
n = t.count("\u00bb")
t = t.replace("\u00bb", chr(96))
p.write_text(t, encoding="utf-8")
print("replaced", n, "closing placeholders")
