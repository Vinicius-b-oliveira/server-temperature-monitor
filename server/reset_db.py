import argparse
import shutil
from datetime import datetime
from pathlib import Path

from app import config, database


def reset(db_path: Path) -> Path | None:
    """Move o banco atual para data/backup e cria um vazio. Devolve o caminho do backup."""
    if not db_path.exists():
        database.init_db(db_path)
        return None

    backup_dir = db_path.parent / "backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = backup_dir / f"{db_path.stem}-{stamp}.db"
    # O -wal pode ter dados ainda não gravados no .db, então vai junto
    for suffix in ("", "-wal", "-shm"):
        source = Path(f"{db_path}{suffix}")
        if source.exists():
            shutil.move(source, f"{backup}{suffix}")

    database.init_db(db_path)
    return backup


def main() -> None:
    parser = argparse.ArgumentParser(description="Apaga os dados do banco, guardando um backup.")
    parser.add_argument("--yes", action="store_true", help="não pede confirmação")
    args = parser.parse_args()

    print(f"Banco: {config.DB_PATH}")
    print("Pare o servidor antes de continuar.")
    if not args.yes and input("Apagar os dados? Digite s para confirmar: ").strip().lower() != "s":
        print("Nada foi alterado.")
        return

    backup = reset(config.DB_PATH)
    if backup is None:
        print("Não havia banco. Um banco vazio foi criado.")
    else:
        print(f"Backup em: {backup}")
        print("Banco vazio criado.")


if __name__ == "__main__":
    main()
