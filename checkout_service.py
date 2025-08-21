# checkout_service.py - Production-ready version
import os
import logging
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import stripe
from dotenv import load_dotenv
import redis
from datetime import datetime
from urllib.parse import urlparse


# Load environment variables
load_dotenv()

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")

# Production vs Development detection
IS_PRODUCTION = os.getenv('FLASK_ENV') == 'production'
PORT = int(os.getenv('PORT', 8080 if IS_PRODUCTION else 5000))

# Stripe configuration
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")

# Redis configuration (optional for now, will use sessions as fallback)
REDIS_URL = os.getenv('REDIS_URL')
redis_client = None

if REDIS_URL:
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        redis_client.ping()
        logger.info("Redis connected successfully")
    except Exception as e:
        logger.warning(f"Redis connection failed, using Flask sessions: {e}")
        redis_client = None

# @contextmanager
# def get_db_connection():
#     """Database connection with enhanced SSL handling"""
#     conn = None
#     try:
#         DATABASE_URL = os.getenv('DATABASE_URL')
        
#         # Determine SSL configuration
#         ssl_mode = os.getenv('DB_SSL_MODE', 'prefer')
#         ssl_cert_file = os.getenv('SSL_CERT_FILE', '/opt/rds-combined-ca-bundle.pem')
        
#         # Log SSL configuration for debugging
#         logger.info(f"Attempting database connection with SSL mode: {ssl_mode}")
        
#         if DATABASE_URL:
#             # Parse DATABASE_URL and build connection
#             result = urlparse(DATABASE_URL)
            
#             # Enhanced connection parameters with SSL
#             conn_params = {
#                 'host': result.hostname,
#                 'port': result.port or 5432,
#                 'database': result.path.lstrip('/'),
#                 'user': result.username,
#                 'password': result.password,
#                 'sslmode': ssl_mode,
#                 'connect_timeout': 10,
#             }
            
#             # Add SSL certificate if using SSL
#             if ssl_mode in ['require', 'verify-ca', 'verify-full']:
#                 if os.path.exists(ssl_cert_file):
#                     conn_params['sslrootcert'] = ssl_cert_file
#                     logger.info(f"Using SSL certificate: {ssl_cert_file}")
#                 else:
#                     logger.warning(f"SSL certificate not found: {ssl_cert_file}")
            
#             conn = psycopg2.connect(**conn_params)
            
#         else:
#             # Individual environment variables approach
#             conn_params = {
#                 'host': os.getenv('DB_HOST') or os.getenv('RDS_HOSTNAME'),
#                 'port': int(os.getenv('DB_PORT') or os.getenv('RDS_PORT', 5432)),
#                 'database': os.getenv('DB_NAME') or os.getenv('RDS_DB_NAME'),
#                 'user': os.getenv('DB_USER') or os.getenv('RDS_USERNAME'),
#                 'password': os.getenv('DB_PASSWORD') or os.getenv('RDS_PASSWORD'),
#                 'sslmode': ssl_mode,
#                 'connect_timeout': 10,
#             }
            
#             # Add SSL certificate if using SSL
#             if ssl_mode in ['require', 'verify-ca', 'verify-full']:
#                 if os.path.exists(ssl_cert_file):
#                     conn_params['sslrootcert'] = ssl_cert_file
#                     logger.info(f"Using SSL certificate: {ssl_cert_file}")
#                 else:
#                     logger.warning(f"SSL certificate not found: {ssl_cert_file}")
            
#             conn = psycopg2.connect(**conn_params)
        
#         # Log successful connection with SSL status
#         ssl_info = conn.get_dsn_parameters().get('sslmode', 'unknown')
#         logger.info(f"Database connected successfully with SSL mode: {ssl_info}")
        
#         yield conn
        
#     except psycopg2.OperationalError as e:
#         error_msg = str(e)
#         logger.error(f"Database connection error: {error_msg}")
        
#         # Provide helpful SSL debugging info
#         if "no pg_hba.conf entry" in error_msg:
#             logger.error("SSL/Authentication issue detected. Check:")
#             logger.error("1. RDS security groups allow your ECS subnet")
#             logger.error("2. RDS parameter group SSL settings")
#             logger.error(f"3. SSL mode is currently: {ssl_mode}")
            
#         if conn:
#             conn.rollback()
#         raise
        
#     except Exception as e:
#         logger.error(f"Unexpected database error: {e}")
#         if conn:
#             conn.rollback()
#         raise
#     finally:
#         if conn:
#             conn.close()

@contextmanager
def get_db_connection():
    """Database connection with enhanced SSL handling"""
    conn = None
    try:
        DATABASE_URL = os.getenv('DATABASE_URL')
        
        # Determine SSL configuration
        ssl_mode = os.getenv('DB_SSL_MODE', 'prefer')
        ssl_cert_file = os.getenv('SSL_CERT_FILE', '/opt/rds-combined-ca-bundle.pem')
        
        # Log SSL configuration for debugging
        logger.info(f"Attempting database connection with SSL mode: {ssl_mode}")
        
        if DATABASE_URL:
            # Parse DATABASE_URL and build connection
            result = urlparse(DATABASE_URL)
            
            # Enhanced connection parameters with SSL
            conn_params = {
                'host': result.hostname,
                'port': result.port or 5432,
                'database': result.path.lstrip('/'),
                'user': result.username,
                'password': result.password,
                'sslmode': ssl_mode,
                'connect_timeout': 10,
                'cursor_factory': RealDictCursor  # ADD THIS LINE
            }
            
            # Add SSL certificate if using SSL
            if ssl_mode in ['require', 'verify-ca', 'verify-full']:
                if os.path.exists(ssl_cert_file):
                    conn_params['sslrootcert'] = ssl_cert_file
                    logger.info(f"Using SSL certificate: {ssl_cert_file}")
                else:
                    logger.warning(f"SSL certificate not found: {ssl_cert_file}")
            
            conn = psycopg2.connect(**conn_params)
            
        else:
            # Individual environment variables approach
            conn_params = {
                'host': os.getenv('DB_HOST') or os.getenv('RDS_HOSTNAME'),
                'port': int(os.getenv('DB_PORT') or os.getenv('RDS_PORT', 5432)),
                'database': os.getenv('DB_NAME') or os.getenv('RDS_DB_NAME'),
                'user': os.getenv('DB_USER') or os.getenv('RDS_USERNAME'),
                'password': os.getenv('DB_PASSWORD') or os.getenv('RDS_PASSWORD'),
                'sslmode': ssl_mode,
                'connect_timeout': 10,
                'cursor_factory': RealDictCursor  # ADD THIS LINE TOO
            }
            
            # Add SSL certificate if using SSL
            if ssl_mode in ['require', 'verify-ca', 'verify-full']:
                if os.path.exists(ssl_cert_file):
                    conn_params['sslrootcert'] = ssl_cert_file
                    logger.info(f"Using SSL certificate: {ssl_cert_file}")
                else:
                    logger.warning(f"SSL certificate not found: {ssl_cert_file}")
            
            conn = psycopg2.connect(**conn_params)
        
        # Log successful connection with SSL status
        ssl_info = conn.get_dsn_parameters().get('sslmode', 'unknown')
        logger.info(f"Database connected successfully with SSL mode: {ssl_info}")
        
        yield conn
        
    except psycopg2.OperationalError as e:
        error_msg = str(e)
        logger.error(f"Database connection error: {error_msg}")
        
        # Provide helpful SSL debugging info
        if "no pg_hba.conf entry" in error_msg:
            logger.error("SSL/Authentication issue detected. Check:")
            logger.error("1. RDS security groups allow your ECS subnet")
            logger.error("2. RDS parameter group SSL settings")
            logger.error(f"3. SSL mode is currently: {ssl_mode}")
            
        if conn:
            conn.rollback()
        raise
        
    except Exception as e:
        logger.error(f"Unexpected database error: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

# Alternative: Simple environment-based SSL configuration
def get_ssl_mode():
    """Determine SSL mode based on environment"""
    # Check explicit override first
    override = os.getenv('DB_SSL_MODE')
    if override:
        return override
    
    # Default based on environment
    env = os.getenv('ENV', 'development').lower()
    if env == 'production':
        return 'require'  # Force SSL in production
    else:
        return 'prefer'   # Try SSL, fallback if needed

# Enhanced health checks
@app.route('/health')
def health_check():
    """Comprehensive health check for load balancers"""
    checks = {}
    overall_status = True
    
    # Database check
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT 1')
        checks['database'] = 'healthy'
    except Exception as e:
        checks['database'] = f'unhealthy: {str(e)}'
        overall_status = False
    
    # Redis check (if configured)
    if redis_client:
        try:
            redis_client.ping()
            checks['redis'] = 'healthy'
        except Exception as e:
            checks['redis'] = f'unhealthy: {str(e)}'
            overall_status = False
    else:
        checks['redis'] = 'not_configured'
    
    # Stripe check
    try:
        stripe.Account.retrieve()
        checks['stripe'] = 'healthy'
    except Exception as e:
        checks['stripe'] = f'unhealthy: {str(e)}'
        overall_status = False
    
    status_code = 200 if overall_status else 503
    response_data = {
        "status": "healthy" if overall_status else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": os.getenv('APP_VERSION', '1.0.0'),
        "environment": "production" if IS_PRODUCTION else "development",
        "checks": checks
    }
    
    return jsonify(response_data), status_code

@app.route('/liveness')
def liveness():
    """Kubernetes liveness probe - just check if app is running"""
    return jsonify({
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }), 200

@app.route('/readiness')
def readiness():
    """Kubernetes readiness probe - check if ready to serve traffic"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT COUNT(*) FROM products LIMIT 1')
        return jsonify({
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            "status": "not_ready", 
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 503

@app.route('/version')
def version():
    """Version information for deployments"""
    return jsonify({
        "version": os.getenv('APP_VERSION', '1.0.0'),
        "deployment_color": os.getenv('DEPLOYMENT_COLOR', 'unknown'),
        "build_timestamp": os.getenv('BUILD_TIMESTAMP'),
        "git_commit": os.getenv('GIT_COMMIT'),
        "environment": "production" if IS_PRODUCTION else "development",
        "port": PORT
    })

# Enhanced cart management (Redis-aware)
def get_cart():
    """Get cart from Redis or session"""
    if redis_client and 'user_id' in session:
        try:
            cart_data = redis_client.get(f"cart:{session['user_id']}")
            return eval(cart_data) if cart_data else {}
        except Exception as e:
            logger.warning(f"Redis cart retrieval failed: {e}")
    
    return session.get('cart', {})

def save_cart(cart):
    """Save cart to Redis or session"""
    if redis_client and 'user_id' in session:
        try:
            redis_client.setex(f"cart:{session['user_id']}", 3600, str(cart))  # 1 hour expiry
            return
        except Exception as e:
            logger.warning(f"Redis cart save failed: {e}")
    
    session['cart'] = cart

# Your original routes (with enhancements)
@app.route('/')
def home():
    # Generate user_id for session if not exists
    if 'user_id' not in session:
        import uuid
        session['user_id'] = str(uuid.uuid4())
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT slug, price FROM products ORDER BY name')
                items = {row['slug']: row['price'] for row in cur.fetchall()}

                cur.execute('''
                    SELECT slug, name, price, description, image_url, 
                           origin_country, brand, material, category, rating, 
                           in_stock, release_date, warranty_months, weight_grams 
                    FROM products WHERE in_stock = true
                    ORDER BY name
                ''')
                coffee_items = {row['slug']: dict(row) for row in cur.fetchall()}

            cart = get_cart()
            return render_template('index.html', 
                                 items=items, 
                                 cart=cart, 
                                 coffee_items=coffee_items)
                                 
    except Exception as e:
        logger.error(f"Error in home route: {e}")
        
        # Check if this is a browser request (wants HTML) or API request (wants JSON)
        accept_header = request.headers.get('Accept', '')
        if 'text/html' in accept_header:
            # Return HTML error page for browser requests
            return f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Coffee Shop - Service Error</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; text-align: center; }}
                    .error-container {{ background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 40px; }}
                    .error-title {{ color: #dc3545; font-size: 24px; margin-bottom: 16px; }}
                    .error-message {{ color: #6c757d; font-size: 16px; margin-bottom: 24px; }}
                    .retry-btn {{ background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block; }}
                    .retry-btn:hover {{ background: #0056b3; color: white; text-decoration: none; }}
                    .error-details {{ font-size: 12px; color: #868e96; margin-top: 20px; font-family: monospace; }}
                </style>
            </head>
            <body>
                <div class="error-container">
                    <div class="error-title">☕ Coffee Shop Temporarily Unavailable</div>
                    <div class="error-message">
                        We're experiencing technical difficulties with our coffee shop. 
                        Our baristas are working to get everything brewing again!
                    </div>
                    <a href="/" class="retry-btn">🔄 Try Again</a>
                    <div class="error-details">
                        Error: {str(e) if not IS_PRODUCTION else 'Please try again in a moment'}
                        <br>Time: {datetime.utcnow().isoformat()}
                    </div>
                </div>
            </body>
            </html>
            ''', 503
        else:
            # Return JSON for API requests
            if IS_PRODUCTION:
                return jsonify({
                    "message": "Service temporarily unavailable",
                    "status": "error"
                }), 503
            else:
                return jsonify({
                    "message": "Service error - check logs",
                    "status": "error",
                    "database_status": "unavailable",
                    "error": str(e)
                }), 503

@app.route('/api/add-to-cart', methods=['POST'])
def api_add_to_cart():
    try:
        data = request.get_json()
        item = data.get('item')
        quantity = int(data.get('quantity', 1))

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT slug, name, price FROM products')
                all_products = {
                    row['slug']: {'name': row['name'], 'price': row['price']}
                    for row in cur.fetchall()
                }

        if item not in all_products:
            return jsonify({'status': 'error', 'message': 'Invalid item'}), 400

        cart = get_cart()
        cart[item] = cart.get(item, 0) + quantity
        save_cart(cart)

        logger.info(f"Item added to cart: {item} x{quantity}")
        return jsonify({'status': 'success', 'cart': cart, 'items': all_products})
    
    except Exception as e:
        logger.error(f"Error in add_to_cart: {e}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart = get_cart()
    if not cart:
        return "Cart is empty", 400

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                if request.method == 'GET':
                    cart_items = []
                    total = 0

                    placeholders = ','.join(['%s'] * len(cart))
                    cur.execute(f"SELECT slug, price FROM products WHERE slug IN ({placeholders})", 
                              list(cart.keys()))
                    prices = {row['slug']: row['price'] for row in cur.fetchall()}

                    for slug, qty in cart.items():
                        price = prices.get(slug, 0)
                        subtotal = price * qty
                        total += subtotal
                        cart_items.append({
                            'item': slug,
                            'quantity': qty,
                            'price': price,
                            'subtotal': subtotal
                        })

                    return render_template("checkout.html", 
                                         items=cart_items, 
                                         total=total / 100.0, 
                                         stripe_public_key=STRIPE_PUBLISHABLE_KEY)

                # POST - process payment
                data = request.form
                required_fields = ["full_name", "email", "address", "city", "state", "zip", "country", "payment_token"]
                
                if not all(data.get(field) for field in required_fields):
                    return jsonify({"status": "failure", "message": "Missing required fields"}), 400

                placeholders = ','.join(['%s'] * len(cart))
                cur.execute(f"SELECT slug, price FROM products WHERE slug IN ({placeholders})", 
                          list(cart.keys()))
                prices = {row['slug']: row['price'] for row in cur.fetchall()}
                total_amount = sum(prices.get(slug, 0) * qty for slug, qty in cart.items())

                try:
                    charge = stripe.Charge.create(
                        amount=total_amount,
                        currency="usd",
                        source=data.get("payment_token"),
                        description=f"Order from {data.get('full_name')}",
                        receipt_email=data.get("email")
                    )
                    logger.info(f"Stripe charge successful: {charge.id}")
                except stripe.error.StripeError as e:
                    logger.error(f"Stripe error: {e}")
                    return jsonify({"status": "failure", "message": str(e)}), 400

                # Save to database
                try:
                    cur.execute("""
                        INSERT INTO transactions (
                            customer_name, customer_email, total_price, status,
                            address, city, state, zip, country
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        data.get("full_name"), data.get("email"), total_amount, 'completed',
                        data.get("address"), data.get("city"), data.get("state"), 
                        data.get("zip"), data.get("country")
                    ))

                    row = cur.fetchone()
                    transaction_id = row['id'] if row else None

                    for slug, qty in cart.items():
                        price_at_purchase = prices.get(slug, 0)
                        cur.execute("""
                            INSERT INTO transaction_items (transaction_id, product_slug, quantity, price_at_purchase)
                            VALUES (%s, %s, %s, %s)
                        """, (transaction_id, slug, qty, price_at_purchase))

                    conn.commit()
                    
                    # Clear cart from Redis/session
                    if redis_client and 'user_id' in session:
                        try:
                            redis_client.delete(f"cart:{session['user_id']}")
                        except:
                            pass
                    session.pop('cart', None)
                    
                    logger.info(f"Order completed: Transaction {transaction_id}")
                    return redirect(url_for('receipt', transaction_id=transaction_id))
                    
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Database transaction error: {e}")
                    return jsonify({"status": "failure", "message": "Database error"}), 500

    except Exception as e:
        logger.error(f"Error in checkout: {e}")
        return jsonify({"status": "failure", "message": "Internal server error"}), 500

@app.route('/api/remove-from-cart', methods=['POST'])
def api_remove_from_cart():
    try:
        data = request.get_json()
        item = data.get('item')
        quantity = int(data.get('quantity', 1))

        if not item:
            return jsonify({'status': 'error', 'message': 'Item is required'}), 400

        # Get all products from database (same as add-to-cart)
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT slug, name, price FROM products')
                all_products = {
                    row['slug']: {'name': row['name'], 'price': row['price']}
                    for row in cur.fetchall()
                }

        if item not in all_products:
            return jsonify({'status': 'error', 'message': 'Invalid item'}), 400

        cart = get_cart()
        
        if item not in cart:
            return jsonify({'status': 'error', 'message': 'Item not in cart'}), 400

        # Remove the specified quantity
        if cart[item] > quantity:
            cart[item] -= quantity
        else:
            # Remove item completely if quantity to remove >= current quantity
            del cart[item]

        save_cart(cart)

        logger.info(f"Item removed from cart: {item} x{quantity}")
        return jsonify({'status': 'success', 'cart': cart, 'items': all_products})
    
    except Exception as e:
        logger.error(f"Error in remove_from_cart: {e}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@app.route('/receipt/<int:transaction_id>')
def receipt(transaction_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT customer_name, customer_email, total_price, address, city, state, zip, country
                    FROM transactions
                    WHERE id = %s
                """, (transaction_id,))
                tx = cur.fetchone()

                if not tx:
                    return "Transaction not found", 404

                cur.execute("""
                    SELECT product_slug, quantity, price_at_purchase
                    FROM transaction_items
                    WHERE transaction_id = %s
                """, (transaction_id,))
                items_raw = cur.fetchall()

        items = []
        for row in items_raw:
            item_name = row['product_slug'].replace('-', ' ').title()
            subtotal = row['quantity'] * row['price_at_purchase']
            items.append({
                'name': item_name,
                'quantity': row['quantity'],
                'subtotal': subtotal / 100.0
            })

        return render_template("receipt.html",
                               customer_name=tx['customer_name'],
                               customer_email=tx['customer_email'],
                               address=tx['address'],
                               city=tx['city'],
                               state=tx['state'],
                               zip=tx['zip'],
                               country=tx['country'],
                               total=tx['total_price'] / 100.0,
                               items=items)
    except Exception as e:
        logger.error(f"Error in receipt route: {e}")
        return "Internal server error", 500

# API endpoints
@app.route('/api/products')
def api_products():
    """Products API endpoint"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT slug, name, price, description, image_url, 
                           origin_country, brand, material, category, rating, 
                           in_stock, release_date, warranty_months, weight_grams 
                    FROM products
                    WHERE in_stock = true
                ''')
                products = {row['slug']: dict(row) for row in cur.fetchall()}
        
        return jsonify({'products': products})
    except Exception as e:
        logger.error(f"Products API error: {e}")
        return jsonify({'error': 'Failed to fetch products'}), 500

# Error handlers for production
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    host = '0.0.0.0' if IS_PRODUCTION else '127.0.0.1'
    debug = not IS_PRODUCTION
    
    print(f"🚀 Starting app in {'PRODUCTION' if IS_PRODUCTION else 'DEVELOPMENT'} mode")
    print(f"   Server: http://{host}:{PORT}")
    print(f"   Environment: {os.getenv('FLASK_ENV', 'development')}")
    print(f"   Redis: {'Connected' if redis_client else 'Not configured'}")
    print("🔧 Available endpoints:")
    print(f"   - Main app: http://{host}:{PORT}/")
    print(f"   - Health: http://{host}:{PORT}/health")
    print(f"   - Version: http://{host}:{PORT}/version")
    
    app.run(debug=debug, host=host, port=PORT)


# Checklist: 
# Create and test your Flask app locally
# Containerize the app using Docker (Write a Dockerfile to package your Flask app and its dependencies into a Docker container so it can run anywhere reliably.)
# Build Docker image and run locally 
# Replace Flask dev with Gunicorn (handle multi thread, concurrency)
# Push Docker image to AWS ECR (private container image storage service in AWS - Github for Docker Images)
# Create ECS Cluster (Fargate mode) (ECS cluster is the logical grouping of your containerized tasks. Using Fargate means AWS runs your containers serverlessly without you managing EC2 instances.)
# Create ECS Task Definition (Define how to run your container (which image, CPU/memory, port mappings, environment variables).)
# Create Security Group for ECS and ALB (created the security group and allowed HTTP traffic, virtual firewall for your AWS resources) 
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! Didn't do ALB yet !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# Create Target Group (list of backend endpoints -- ECS containers running your app) for ECS service: (the Target Group tells the Load Balancer: “Hey, send the web traffic to these containers on this port.”)
# Run Task on ECS with Fargate (No Load Balancer Yet): 1 container task on ECS using Fargate
# Get pulic ip of the task in browser

## This is the ECR-url: 864572275930.dkr.ecr.us-east-1.amazonaws.com/checkout-app

# To start task again: 
# docker push 864572275930.dkr.ecr.us-east-1.amazonaws.com/checkout-app:latest (just to confirm)
# aws ecs run-task --cluster checkout-cluster --task-definition checkout-task --launch-type FARGATE --network-configuration "awsvpcConfiguration={subnets=[subnet-09935490108a56234],securityGroups=[sg-05ca477da956da8af],assignPublicIp=ENABLED}"
# List running tasks: aws ecs list-tasks --cluster checkout-cluster
# Describe the new task (use the task ARN from above): aws ecs describe-tasks --cluster checkout-cluster --tasks <task-arn>
# Get the ENI ID from the response: Look under "attachments" → "details" → "networkInterfaceId": aws ec2 describe-network-interfaces --network-interface-ids <eni-id>
# Go to: http://<PublicIp>:5000 (inbrowser)
#To stop: aws ecs stop-task --cluster checkout-cluster --task <task-id>

# Will create and delete the ALB when not using it (for Blue-Green deployment)


# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! ALB !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# Didn't create ALB yet because it cost money but will do these 3 steps later down the line:
# So your approach can be:
    # For now (development/testing):
        # Create the ECS cluster, task definitions, run tasks manually (maybe without ALB).
        # Access the service directly via task IP or public IP.
    # Later (production/deployment):
        # Create ALB, target groups, listeners.
        # Create ECS service with ALB integration to handle scalable traffic and better routing.

### Create Load Balancer (ALB): command
# aws elbv2 create-load-balancer \
#   --name checkout-alb \
#   --subnets <subnet-1> <subnet-2> \
#   --security-groups <sg-id> \
#   --scheme internet-facing
### Create Listener on ALB: command
# aws elbv2 create-listener \
#   --load-balancer-arn <alb-arn> \
#   --protocol HTTP \
#   --port 80 \
#   --default-actions Type=forward,TargetGroupArn=<target-group-arn>
### Create ECS Service with ALB integration: command
# aws ecs create-service \
#   --cluster checkout-cluster \
#   --service-name checkout-service \
#   --task-definition checkout-task \
#   --desired-count 1 \
#   --launch-type FARGATE \
#   --network-configuration "awsvpcConfiguration={subnets=[<subnet-1>,<subnet-2>],securityGroups=[<sg-id>],assignPublicIp=ENABLED}" \
#   --load-balancers "targetGroupArn=<target-group-arn>,containerName=checkout-container,containerPort=5000"

# subnet to create ECS service with ALB intergration
# --------------------------------------------------
# |                 DescribeSubnets                |
# +-------------------+----------------------------+
# | AvailabilityZone  |         SubnetId           |
# +-------------------+----------------------------+
# |  us-east-1c       |  subnet-0e4a6afe3d6171d7a  |
# |  us-east-1d       |  subnet-0412c1557bd9f2dea  |
# |  us-east-1f       |  subnet-009ac20d265bb2c5d  |
# |  us-east-1a       |  subnet-09935490108a56234  |
# |  us-east-1e       |  subnet-07a4d9e1bd7e170dc  |
# |  us-east-1b       |  subnet-0677ec7484b485156  |
# +-------------------+----------------------------+



# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! RDMS !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# cost about 30$ monthly