from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def home(request):
    html_content = """
    <html>
        <head>
            <title>Welcome</title>
            <style>
                body {
                    margin: 0;
                    padding: 0;
                    background: linear-gradient(135deg, #f6d365, #fda085);
                    font-family: 'Poppins', sans-serif;
                    color: #333;
                    text-align: center;
                }
                .container {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    padding: 20px;
                }
                .banner {
                    width: 80%;
                    max-width: 900px;
                    border-radius: 15px;
                    overflow: hidden;
                    box-shadow: 0 6px 20px rgba(0,0,0,0.25);
                    margin-bottom: 40px;
                    transition: transform 0.4s ease, box-shadow 0.4s ease;
                }
                .banner:hover {
                    transform: scale(1.03);
                    box-shadow: 0 10px 25px rgba(0,0,0,0.35);
                }
                .banner img {
                    width: 100%;
                    height: 350px;
                    object-fit: cover;
                }
                h1 {
                    color: #fff;
                    text-shadow: 2px 2px 8px rgba(0,0,0,0.4);
                    font-size: 48px;
                    margin-bottom: 10px;
                }
                p {
                    background: rgba(255,255,255,0.8);
                    display: inline-block;
                    padding: 12px 24px;
                    border-radius: 10px;
                    font-size: 20px;
                    box-shadow: 0 0 10px rgba(0,0,0,0.15);
                }
                footer {
                    margin-top: 40px;
                    font-size: 14px;
                    color: rgba(255,255,255,0.85);
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="banner">
                    <img src="/static/images/Ecommerce.jpg" alt="E-commerce Banner">
                </div>
                <h1>🛍️ Welcome to My E-Commerce Project</h1>
                <p>Serving JSON in style ✨</p>
                <footer>Powered by Django | Local Development Server</footer>
            </div>
        </body>
    </html>
    """
    return HttpResponse(html_content)
