import os
import resend
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

resend.api_key = os.getenv("RESEND_API_KEY")

def send_new_vacancies_email(new_vacancies_count: int, dashboard_url: str = "#") -> bool:
    """
    Envía un correo notificando el número de vacantes nuevas y un botón al dashboard.
    """
    if not resend.api_key:
        print("Advertencia: No hay RESEND_API_KEY configurada. Correo no enviado.")
        return False
        
    sender_email = os.getenv("RESEND_SENDER_EMAIL", "onboarding@resend.dev")
    recipient_email = os.getenv("RESEND_RECIPIENT_EMAIL")
    
    if not recipient_email:
        print("Advertencia: No hay RESEND_RECIPIENT_EMAIL configurada. Correo no enviado.")
        return False

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; text-align: center; }}
            .btn {{ 
                display: inline-block; 
                padding: 12px 24px; 
                margin: 20px 0; 
                background-color: #007bff; 
                color: #ffffff; 
                text-decoration: none; 
                border-radius: 5px; 
                font-weight: bold;
            }}
            .footer {{ font-size: 12px; color: #777; margin-top: 30px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Nuevas vacantes descubiertas 🚀</h2>
            <p style="font-size: 18px;">Se encontraron <strong>{new_vacancies_count}</strong> nuevas vacantes en la última comprobación.</p>
            <a href="{dashboard_url}" class="btn">Ir al Dashboard</a>
            <div class="footer">
                <p>Este es un correo automático generado por Job Monitor.</p>
            </div>
        </div>
    </body>
    </html>
    """

    try:
        response = resend.Emails.send({
            "from": sender_email,
            "to": [recipient_email],
            "subject": f"Nuevas vacantes descubiertas ({new_vacancies_count})",
            "html": html_content
        })
        return True
    except Exception as e:
        print(f"Error al enviar correo vía Resend: {e}")
        return False
