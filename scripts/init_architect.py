#!/usr/bin/env python3
"""
Inicializar el primer humano ARQUITECTO en ODI.
Genera secreto TOTP para Google Authenticator/Authy.
"""
import os
import sys
import asyncio

from dotenv import load_dotenv
load_dotenv("/opt/odi/.env")

async def main():
    try:
        import pyotp
        import asyncpg
    except ImportError:
        print("Instalar: pip install pyotp asyncpg --break-system-packages")
        sys.exit(1)

    totp_secret = pyotp.random_base32()
    totp = pyotp.TOTP(totp_secret)
    uri = totp.provisioning_uri(
        name="JuanDavid@ODI",
        issuer_name="ODI Industrial"
    )

    pool = await asyncpg.create_pool(
        host=os.getenv("POSTGRES_HOST", "172.18.0.4"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "odi_user"),
        password=os.getenv("POSTGRES_PASSWORD", "odi_secure_password"),
        database=os.getenv("POSTGRES_DB", "odi"),
        min_size=1, max_size=2
    )

    async with pool.acquire() as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM odi_humans WHERE human_id = 'JD'"
        )
        if exists:
            print("ARQUITECTO JD ya existe. Usar /odi/auth/login para obtener JWT.")
            await pool.close()
            return

        await conn.execute("""
            INSERT INTO odi_humans (human_id, display_name, role, vertical_scope, totp_secret)
            VALUES ('JD', 'Juan David Jiménez', 'ARQUITECTO', '*', $1)
        """, totp_secret)

    await pool.close()

    print("=" * 60)
    print("  ARQUITECTO JD CREADO")
    print("=" * 60)
    print()
    print(f"  TOTP Secret: {totp_secret}")
    print(f"  URI (para QR): {uri}")
    print()
    print("  GUARDAR ESTE SECRETO EN UN LUGAR SEGURO")
    print("  NO SE PUEDE RECUPERAR DESPUES")
    print()
    print("  Escanear QR en Google Authenticator o Authy")
    print("  para obtener codigos de 6 digitos.")
    print()
    print("  Flujo de uso:")
    print("  1. POST /odi/auth/login {human_id: 'JD', totp_code: '123456'}")
    print("  2. Recibe JWT (valido 10 min)")
    print("  3. POST /odi/override con Authorization: Bearer <JWT> + X-ODI-TOTP: <code>")
    print("=" * 60)

asyncio.run(main())
