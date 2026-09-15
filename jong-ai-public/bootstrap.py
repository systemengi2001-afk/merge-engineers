from pathlib import Path
import zipfile, shutil
p=Path(__file__).with_name('app.zip')
out=Path(__file__).with_name('app')
if out.exists():
    shutil.rmtree(out)
out.mkdir()
with zipfile.ZipFile(p) as z:
    z.extractall(out)
