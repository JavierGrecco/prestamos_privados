"""Migración v014: hace inmutable la evidencia de auditoría."""


def aplicar(db) -> None:
    db.ejecutar(
        """
        CREATE TRIGGER IF NOT EXISTS trg_auditoria_no_update
        BEFORE UPDATE ON auditoria
        BEGIN
            SELECT RAISE(ABORT, 'La auditoría es inmutable');
        END
        """
    )
    db.ejecutar(
        """
        CREATE TRIGGER IF NOT EXISTS trg_auditoria_no_delete
        BEFORE DELETE ON auditoria
        BEGIN
            SELECT RAISE(ABORT, 'La auditoría no se elimina');
        END
        """
    )
