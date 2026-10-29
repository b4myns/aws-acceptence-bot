#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Nom du script : send_aws_acceptances_auto_discord.py
Description   : Automatisation de l'envoi d'emails d'acceptation AWS Cloud Club USTHB.
                1. Génère un lien d'invitation Discord unique (max_uses=1) via l'API Discord.
                2. Envoie l'e-mail avec le design officiel AWS Cloud Club USTHB.
                3. Écrit le lien généré en colonne C et le statut "ENVOYÉ" en colonne D.
"""
import os
from pathlib import Path
from email.mime.image import MIMEImage
import hashlib
import html
import re
import unicodedata
from datetime import datetime, timedelta, timezone
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import gspread
from google.oauth2.service_account import Credentials
import requests


def load_local_env():
    """Load simple KEY=VALUE settings from the ignored .env file."""
    env_path = Path(__file__).with_name(".env")
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


load_local_env()

# ==============================================================================
# 1. PARAMÈTRES DISCORD API
# ==============================================================================
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
DISCORD_CHANNEL_ID = os.environ.get("DISCORD_CHANNEL_ID", "").strip()

# ==============================================================================
# 2. PARAMÈTRES GOOGLE SHEETS
# ==============================================================================
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "").strip()
CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS_FILE", "credentials.json").strip()
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ==============================================================================
# 3. PARAMÈTRES SMTP GMAIL (Port 587 STARTTLS)
# ==============================================================================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = os.environ.get("SMTP_SENDER_EMAIL", "").strip()
APP_PASSWORD = os.environ.get("SMTP_APP_PASSWORD", "").strip()

# ==============================================================================
# 4. PARAMÈTRES DU MESSAGE
# ==============================================================================
SUBJECT = "Bienvenue dans l'aventure — AWS Cloud Club USTHB ☁️🚀"


def create_discord_invite() -> str:
    """Génère une invitation unique (1 utilisation max, expire après 7 jours) via l'API Discord."""
    url = f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/invites"
    token = DISCORD_BOT_TOKEN.removeprefix("Bot ").strip()
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN is missing from .env")
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "max_age": 604800,  # 7 jours
        "max_uses": 1,       # 1 seule utilisation
        "unique": True
    }

    response = requests.post(url, headers=headers, json=payload, timeout=10)
    if response.status_code in (200, 201):
        invite_code = response.json().get("code")
        return f"https://discord.gg/{invite_code}"
    elif response.status_code == 401:
        raise RuntimeError("Discord rejected DISCORD_BOT_TOKEN (401). Use the current bot token from Discord Developer Portal.")
    else:
        raise RuntimeError(f"Erreur API Discord ({response.status_code}) : {response.text}")


def build_html_template(prenom: str, email: str, lien_discord: str) -> str:
    """Intègre le design AWS Cloud Club USTHB (thème sombre) au format compatible e-mail."""

    # ---- Réglages à adapter ----
    logo_url = "https://raw.githubusercontent.com/b4myns/aws-usthb-logo/main/logo2.png"
    educate_url = "https://www.awseducate.com/"
    builder_groups_url = "https://builder.aws.com/community/groups"
    linkedin_url = "https://www.linkedin.com/groups/42836141/"  # TODO : lien LinkedIn du club
    signature = "L'équipe"
    hero_block = ""   # optionnel : doit être une ligne <tr>...</tr>
    event_block = ""  # optionnel : doit être une ligne <tr>...</tr>

    # ---- Valeurs dynamiques ----
    # Slug affiché dans le faux terminal : "Yacine Amrâoui" -> "yacine-amraoui"
    ascii_name = unicodedata.normalize("NFKD", prenom).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-") or "builder"

    # Pass ID stable dérivé de l'e-mail : CC-3F9A1B
    pass_id = "CC-" + hashlib.sha1(email.lower().encode("utf-8")).hexdigest()[:6].upper()

    # Date d'expiration réelle de l'invitation Discord (repli : aujourd'hui + 7 jours)
    expiry = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%d/%m/%Y")
    try:
        code = lien_discord.rstrip("/").rsplit("/", 1)[-1]
        r = requests.get(
            f"https://discord.com/api/v10/invites/{code}",
            params={"with_expiration": "true"},
            timeout=10,
        )
        if r.status_code == 200 and r.json().get("expires_at"):
            expiry = datetime.fromisoformat(r.json()["expires_at"]).strftime("%d/%m/%Y")
    except Exception:
        pass

    template = r"""<!DOCTYPE html>
<html lang="fr" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="x-apple-disable-message-reformatting">
  <title>Bienvenue chez AWS Cloud Club USTHB</title>
  <!--[if mso]>
  <noscript><xml><o:OfficeDocumentSettings><o:AllowPNG/><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript>
  <![endif]-->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;700;800&display=swap" rel="stylesheet">
  <style type="text/css">
    body, table, td, a { -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }
    table, td { mso-table-lspace: 0pt; mso-table-rspace: 0pt; }
    img { -ms-interpolation-mode: bicubic; border: 0; height: auto; line-height: 100%; outline: none; text-decoration: none; }
    table { border-collapse: collapse !important; }
    body { height: 100% !important; margin: 0 !important; padding: 0 !important; width: 100% !important; }
    a[x-apple-data-detectors] { color: inherit !important; text-decoration: none !important; font-size: inherit !important; font-family: inherit !important; font-weight: inherit !important; line-height: inherit !important; }

    .btn-action:hover { background-color: #E08200 !important; }
    .social-link:hover { color: #FF9900 !important; }

    @media screen and (max-width: 620px) {
      .wrapper { width: 100% !important; max-width: 100% !important; }
      .canvas-pad { padding: 16px 8px 36px 8px !important; }
      .main-pad { padding: 28px 18px !important; }
      .header-title { font-size: 28px !important; line-height: 34px !important; }
      .ticket-pad { padding: 18px 16px !important; }
      .field-col { display: block !important; width: 100% !important; padding: 0 0 14px 0 !important; box-sizing: border-box !important; }
      .email-val { word-break: break-all !important; }
      .step-col { display: block !important; width: 100% !important; max-width: 100% !important; box-sizing: border-box !important; }
      .step-gap { display: block !important; width: 100% !important; height: 10px !important; }
      .step-1 { border-radius: 24px 24px 10px 10px !important; }
      .step-2 { border-radius: 10px !important; }
      .step-3 { border-radius: 10px 10px 24px 24px !important; }
      .hero-img { width: 100% !important; height: auto !important; }
    }
  </style>
</head>
<body style="margin: 0; padding: 0; background-color: #0B1017; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale;">

  <!-- PREHEADER -->
  <div style="display: none; max-height: 0px; overflow: hidden; mso-hide: all;">
    Candidature retenue, %%PRENOM%%. Ton Builder Key est prêt (usage unique, expire le %%EXPIRY%%).
    &#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;
  </div>

  <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0" bgcolor="#0B1017" style="background-color: #0B1017;">
    <tr>
      <td align="center" class="canvas-pad" style="padding: 32px 16px 64px 16px;">

        <table role="presentation" class="wrapper" width="100%" border="0" cellpadding="0" cellspacing="0" style="max-width: 620px; width: 100%;">

          <!-- 1. HEADER -->
          <tr>
            <td align="center" style="padding: 0 0 32px 0;">
              <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding-bottom: 12px;">
                  <img src="%%LOGO_URL%%" width="56" height="56" alt="AWS Cloud Club" style="display: block; width: 56px; height: 56px;" />                  </td>
                </tr>
                <tr>
                  <td align="center" style="font-family: 'JetBrains Mono', 'Courier New', Courier, monospace; font-size: 11px; font-weight: 700; color: #FF9900; letter-spacing: 0.15em; text-transform: uppercase; padding-bottom: 20px;">
                    AWS CLOUD CLUB &bull; USTHB ALGER
                  </td>
                </tr>
                <tr>
                  <td align="center" class="header-title" style="font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Inter', sans-serif; font-size: 32px; line-height: 38px; font-weight: 900; color: #00E57F; letter-spacing: -0.03em; text-transform: uppercase; padding-bottom: 14px;">
                    BIENVENUE DANS<br>LES NUAGES
                  </td>
                </tr>
                <tr>
                  <td align="center" style="padding-top: 4px;">
                    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="180">
                      <tr>
                        <td width="70" height="2" style="background-color: #FF9900; font-size: 1px; line-height: 1px;">&nbsp;</td>
                        <td width="40" align="center" style="font-family: 'JetBrains Mono', monospace; font-size: 14px; color: #FF9900; line-height: 1px;">&#9670;</td>
                        <td width="70" height="2" style="background-color: #FF9900; font-size: 1px; line-height: 1px;">&nbsp;</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- 2. MAIN CARD -->
          <tr>
            <td bgcolor="#131B26" class="main-pad" style="background-color: #131B26; border: 1px solid #1E2B3C; border-radius: 16px; padding: 40px 36px;">
              <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">

                <tr>
                  <td align="left" style="padding-bottom: 22px; font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Inter', sans-serif; font-size: 22px; line-height: 28px; font-weight: 700; color: #FFFFFF;">
                    Salut %%PRENOM%% !
                  </td>
                </tr>
                <tr>
                  <td align="left" style="padding-bottom: 18px; font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Inter', sans-serif; font-size: 15px; line-height: 24px; color: #94A3B8;">
                    Nous avons pris le temps d’étudier chaque dossier. Aujourd’hui, nous t’ouvrons officiellement les portes du <strong style="color: #FFFFFF; font-weight: 600;">noyau de Builders de l’AWS Cloud Club USTHB</strong>.
                  </td>
                </tr>
                <tr>
                  <td align="left" style="padding-bottom: 28px; font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Inter', sans-serif; font-size: 15px; line-height: 24px; color: #94A3B8;">
                    Ici, on apprend le cloud et l’IA en construisant de vrais projets, aux côtés d’étudiants de plus de 600 campus dans le monde. Que tu débutes ou que tu codes depuis des années, c’est l’endroit pour rencontrer des pairs, apprendre d’experts AWS et construire à ton rythme.
                  </td>
                </tr>

                %%HERO_BLOCK%%

                <!-- TERMINAL BOOT LOG -->
                <tr>
                  <td align="left" style="padding-bottom: 28px;">
                    <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0" bgcolor="#0A0E14" style="background-color: #0A0E14; border: 1px solid #1E2B3C; border-radius: 12px;">
                      <tr>
                        <td style="padding: 12px 18px; border-bottom: 1px solid #1E2B3C; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 11px; line-height: 14px; letter-spacing: 0.1em; color: #5F6B7A;">
                          <span style="color: #FF9900;">&#9679;</span> <span style="color: #5F6B7A;">&#9679;</span> <span style="color: #00E57F;">&#9679;</span>&nbsp;&nbsp; cloud-club@usthb ~ acceptance.log
                        </td>
                      </tr>
                      <tr>
                        <td class="ticket-pad" style="padding: 18px; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 12px; line-height: 22px; color: #E2E8F0;">
                          <span style="color: #5F6B7A;">$</span> aws cloud-club accept --member <span style="color: #FF9900;">%%SLUG%%</span><br>
                          <span style="color: #00E57F;">&#10004;</span> candidature validée<br>
                          <span style="color: #00E57F;">&#10004;</span> builder key générée <span style="color: #5F6B7A;">&rarr; %%PASS_ID%%</span><br>
                          <span style="color: #FF9900;">&hellip;</span> en attente de ta connexion
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>

                <!-- 3. BUILDER KEY (boarding pass) -->
                <tr>
                  <td align="left" style="padding-bottom: 28px;">
                    <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0" bgcolor="#0A0E14" style="background-color: #0A0E14; border: 1px solid #1E2B3C; border-radius: 12px;">
                      <tr>
                        <td class="ticket-pad" style="padding: 26px 28px 20px 28px;">
                          <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
                            <tr>
                              <td align="left" style="font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 11px; font-weight: 700; color: #FF9900; letter-spacing: 0.1em; text-transform: uppercase;">// BUILDER KEY</td>
                              <td align="right" style="font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 11px; color: #00E57F; letter-spacing: 0.1em;">&#9679; ACTIF</td>
                            </tr>
                            <tr>
                              <td colspan="2" style="padding-top: 12px; font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Inter', sans-serif; font-size: 22px; line-height: 28px; font-weight: 700; letter-spacing: -0.02em; color: #FFFFFF;">Ton accès au serveur Discord</td>
                            </tr>
                          </table>
                        </td>
                      </tr>

                      <!-- perforation + notches -->
                      <tr>
                        <td style="padding: 0;">
                          <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
                            <tr>
                              <td width="10" height="20" bgcolor="#131B26" style="width: 10px; height: 20px; font-size: 0; line-height: 0; background-color: #131B26; border-radius: 0 10px 10px 0;">&nbsp;</td>
                              <td style="font-size: 0; line-height: 0; border-top: 1px dashed #1E2B3C; height: 1px;">&nbsp;</td>
                              <td width="10" height="20" bgcolor="#131B26" style="width: 10px; height: 20px; font-size: 0; line-height: 0; background-color: #131B26; border-radius: 10px 0 0 10px;">&nbsp;</td>
                            </tr>
                          </table>
                        </td>
                      </tr>

                      <tr>
                        <td class="ticket-pad" style="padding: 4px 28px 26px 28px;">
                          <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
                            <tr>
                              <td class="field-col" width="50%" valign="top" style="width: 50%; padding-right: 10px;">
                                <div style="font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 10px; line-height: 14px; letter-spacing: 0.12em; text-transform: uppercase; color: #5F6B7A;">Pass ID</div>
                                <div style="padding-top: 4px; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 14px; line-height: 20px; font-weight: 500; color: #FFFFFF;">%%PASS_ID%%</div>
                              </td>
                              <td class="field-col" width="50%" valign="top" style="width: 50%; padding-left: 10px;">
                                <div style="font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 10px; line-height: 14px; letter-spacing: 0.12em; text-transform: uppercase; color: #5F6B7A;">Expire le</div>
                                <div style="padding-top: 4px; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 14px; line-height: 20px; font-weight: 500; color: #FFFFFF;">%%EXPIRY%%</div>
                              </td>
                            </tr>
                          </table>

                          <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0" style="margin-top: 16px;">
                            <tr>
                              <td bgcolor="#131B26" style="background-color: #131B26; border: 1px solid #1E2B3C; border-radius: 8px; padding: 12px 14px;">
                                <div style="font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 10px; line-height: 14px; letter-spacing: 0.12em; text-transform: uppercase; color: #5F6B7A;">Lié à</div>
                                <div class="email-val" style="padding-top: 4px; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 14px; line-height: 20px; color: #FFFFFF;">%%EMAIL%%</div>
                              </td>
                            </tr>
                          </table>

                          <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
                            <tr>
                              <td style="padding-top: 16px; font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Inter', sans-serif; font-size: 13px; line-height: 20px; color: #94A3B8;">
                                <span style="color: #FF9900; font-weight: 700;">Usage unique.</span> Ce lien est strictement personnel et s’invalide dès ta première connexion. Ne le partage avec personne.
                              </td>
                            </tr>
                          </table>

                          <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0" style="margin-top: 22px;">
                            <tr>
                              <td align="center" bgcolor="#FF9900" class="btn-action" style="background-color: #FF9900; border-radius: 8px; text-align: center;">
                                <a href="%%LIEN_DISCORD%%" target="_blank" style="display: block; padding: 16px 20px; mso-padding-alt: 16px 20px; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 14px; font-weight: 800; color: #0B1017; text-decoration: none; letter-spacing: -0.01em;">
                                  Rejoindre le Discord &rarr;
                                </a>
                              </td>
                            </tr>
                          </table>

                          <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
                            <tr>
                              <td align="center" style="padding-top: 16px; font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Inter', sans-serif; font-size: 13px; line-height: 20px; color: #94A3B8;">
                                Pas encore de compte ? Commence par <a href="%%EDUCATE_URL%%" target="_blank" style="color: #00E57F; font-weight: 600; text-decoration: underline;">AWS Educate</a>.
                              </td>
                            </tr>
                          </table>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>

                %%EVENT_BLOCK%%

                <!-- 4. ONBOARDING PROTOCOL -->
                <tr>
                  <td align="left" style="padding-bottom: 8px;">
                    <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
                      <tr>
                        <td align="left" style="font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 11px; font-weight: 700; color: #FF9900; letter-spacing: 0.08em; text-transform: uppercase;">// PROTOCOLE D’INTÉGRATION</td>
                        <td align="right" style="font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 11px; color: #00E57F;">[01 &rarr; 03]</td>
                      </tr>
                    </table>
                  </td>
                </tr>
                <tr>
                  <td align="left" style="padding-bottom: 32px;">
                    <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
                      <tr>
                        <td width="31.5%" valign="top" bgcolor="#0A0E14" class="step-col step-1" style="background-color: #0A0E14; border: 1px solid #1E2B3C; border-radius: 32px 12px 12px 32px; padding: 20px 16px;">
                          <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
                            <tr><td style="font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700; color: #FF9900; padding-bottom: 8px;">01 // CHARTE</td></tr>
                            <tr><td style="font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif; font-size: 14px; font-weight: 700; color: #FFFFFF; padding-bottom: 4px;">Accueil</td></tr>
                            <tr><td style="font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif; font-size: 12px; line-height: 18px; color: #94A3B8;">Lis <span style="font-family: 'JetBrains Mono', monospace; color: #FFFFFF;">#règlement</span> et présente-toi.</td></tr>
                          </table>
                        </td>
                        <td width="2.75%" class="step-gap" style="font-size: 1px; line-height: 1px;">&nbsp;</td>
                        <td width="31.5%" valign="top" bgcolor="#0A0E14" class="step-col step-2" style="background-color: #0A0E14; border: 1px solid #1E2B3C; border-radius: 12px; padding: 20px 16px;">
                          <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
                            <tr><td style="font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700; color: #AD5CFF; padding-bottom: 8px;">02 // RÔLES</td></tr>
                            <tr><td style="font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif; font-size: 14px; font-weight: 700; color: #FFFFFF; padding-bottom: 4px;">Accès</td></tr>
                            <tr><td style="font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif; font-size: 12px; line-height: 18px; color: #94A3B8;">Choisis tes rôles dans <span style="font-family: 'JetBrains Mono', monospace; color: #FFFFFF;">#rôles</span>.</td></tr>
                          </table>
                        </td>
                        <td width="2.75%" class="step-gap" style="font-size: 1px; line-height: 1px;">&nbsp;</td>
                        <td width="31.5%" valign="top" bgcolor="#0A0E14" class="step-col step-3" style="background-color: #0A0E14; border: 1px solid #1E2B3C; border-radius: 12px 32px 32px 12px; padding: 20px 16px;">
                          <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
                            <tr><td style="font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700; color: #00E57F; padding-bottom: 8px;">03 // BUILD</td></tr>
                            <tr><td style="font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif; font-size: 14px; font-weight: 700; color: #FFFFFF; padding-bottom: 4px;">Labs</td></tr>
                            <tr><td style="font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif; font-size: 12px; line-height: 18px; color: #94A3B8;">Lance ton premier lab et construis.</td></tr>
                          </table>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>

                <!-- SIGN-OFF -->
                <tr>
                  <td align="left" style="border-top: 1px solid #1E2B3C; padding-top: 24px;">
                    <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
                      <tr>
                        <td align="left" style="font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Inter', sans-serif; font-size: 15px; line-height: 24px; font-weight: 600; color: #FFFFFF; padding-bottom: 6px;">
                          Une question ? Réponds simplement à cet e-mail, on lit tout. On est ravis de t’avoir avec nous. Let’s build !
                        </td>
                      </tr>
                      <tr>
                        <td align="left" style="font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 11px; font-weight: 700; color: #FF9900; letter-spacing: 0.08em; text-transform: uppercase; padding-bottom: 12px;">
                          &mdash; AVEC AMITIÉ &bull; AWS CLOUD CLUB
                        </td>
                      </tr>
                      <tr>
                        <td align="left" style="font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Inter', sans-serif; font-size: 15px; font-weight: 800; color: #FFFFFF;">
                          %%SIGNATURE%% <span style="color: #5F6B7A; font-weight: 400;">&bull;</span> <span style="font-weight: 400; color: #94A3B8;">AWS Cloud Club USTHB</span>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>

              </table>
            </td>
          </tr>

          <!-- 5. FOOTER -->
          <tr>
            <td align="center" style="padding-top: 32px;">
              <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding-bottom: 18px; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 12px; color: #475569; letter-spacing: 0.15em;">
                    _ ( &#9729; ) _ ( &#9729; ) _
                  </td>
                </tr>
                <tr>
                  <td align="center" style="padding-bottom: 16px; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 12px; color: #94A3B8;">
                    <a href="%%BUILDER_GROUPS_URL%%" target="_blank" class="social-link" style="color: #FFFFFF; font-weight: 600; text-decoration: none; border-bottom: 2px solid #FF9900; padding-bottom: 2px;">Builder Groups</a>
                    <span style="color: #475569; padding: 0 12px;">//</span>
                    <a href="%%LINKEDIN_URL%%" target="_blank" class="social-link" style="color: #FFFFFF; font-weight: 600; text-decoration: none; border-bottom: 2px solid #FF9900; padding-bottom: 2px;">LinkedIn</a>
                  </td>
                </tr>
                <tr>
                  <td align="center" style="font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 11px; line-height: 18px; color: #475569;">
                     AWS Cloud Club &bull; USTHB, Bab Ezzouar, Alger, Algérie<br>
                    <span style="font-size: 10px; letter-spacing: 0.08em;">LA TÊTE DANS LES NUAGES, LES PIEDS SUR TERRE.</span>
                </tr>
              </table>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    values = {
        "PRENOM": html.escape(prenom),
        "EMAIL": html.escape(email),
        "SLUG": html.escape(slug),
        "PASS_ID": pass_id,
        "EXPIRY": expiry,
        "LIEN_DISCORD": html.escape(lien_discord, quote=True),
        "LOGO_URL": html.escape(logo_url, quote=True),
        "EDUCATE_URL": html.escape(educate_url, quote=True),
        "BUILDER_GROUPS_URL": html.escape(builder_groups_url, quote=True),
        "LINKEDIN_URL": html.escape(linkedin_url, quote=True),
        "SIGNATURE": html.escape(signature),
        "HERO_BLOCK": hero_block,
        "EVENT_BLOCK": event_block,
    }
    for key, val in values.items():
        template = template.replace(f"%%{key}%%", val)
    return template



def main():
  required = {
    "DISCORD_BOT_TOKEN": DISCORD_BOT_TOKEN,
    "DISCORD_CHANNEL_ID": DISCORD_CHANNEL_ID,
    "SPREADSHEET_ID": SPREADSHEET_ID,
    "SMTP_SENDER_EMAIL": SENDER_EMAIL,
    "SMTP_APP_PASSWORD": APP_PASSWORD,
  }
  missing = [name for name, value in required.items() if not value]
  if missing:
    print("[ERREUR] Variables manquantes dans .env : " + ", ".join(missing))
    return

  # 1. Connexion Google Sheets
  print("[1/3] Connexion à Google Sheets...")
  try:
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
  except Exception as e:
    print(f"[ERREUR] Connexion Google Sheets : {e}")
    return

  rows = sheet.get_all_values()
  if len(rows) <= 1:
    print("Aucun candidat à traiter.")
    return

  print(f"[2/3] Données chargées : {len(rows) - 1} ligne(s).")

  # 2. Connexion SMTP Gmail (STARTTLS port 587)
  print("[3/3] Connexion au serveur SMTP Gmail...")
  try:
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(SENDER_EMAIL, APP_PASSWORD)
    print("Connexion SMTP réussie. Début des envois...\n")
  except Exception as e:
    print(f"[ERREUR] Connexion SMTP : {e}")
    return

  sent_count = 0

  for row_idx, row in enumerate(rows[1:], start=2):
    prenom = row[0].strip() if len(row) > 0 else ""
    email = row[1].strip() if len(row) > 1 else ""
    existing_link = row[2].strip() if len(row) > 2 else ""
    statut = row[3].strip() if len(row) > 3 else ""

    if not email or statut.upper() == "ENVOYÉ":
      continue

    # Récupération ou création du lien Discord unique
    if existing_link and existing_link.startswith("https://discord.gg/"):
      lien_discord = existing_link
    else:
      try:
        lien_discord = create_discord_invite()
        sheet.update_cell(row_idx, 3, lien_discord)
      except Exception as err:
        print(f"✖ Échec création lien Discord pour {prenom} ({email}) : {err}")
        continue

    # Assemblage de l'email
    msg = MIMEMultipart("alternative")
    msg["Subject"] = SUBJECT
    msg["From"] = f"AWS Cloud Club USTHB <{SENDER_EMAIL}>"
    msg["To"] = email
    msg.attach(MIMEText(build_html_template(prenom, email, lien_discord), "html", "utf-8"))

    # Envoi
    try:
      server.sendmail(SENDER_EMAIL, email, msg.as_string())
      print(f"✔ Envoyé à : {prenom} ({email}) | Discord : {lien_discord}")
      sheet.update_cell(row_idx, 4, "ENVOYÉ")
      sent_count += 1
      time.sleep(1)
    except Exception as e:
      print(f"✖ Échec d'envoi pour {email} : {e}")

  server.quit()
  print(f"\nTraitement terminé : {sent_count} email(s) envoyé(s) avec succès.")

if __name__ == "__main__":
  main()