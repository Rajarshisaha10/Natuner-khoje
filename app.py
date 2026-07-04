from pathlib import Path
import sqlite3
from datetime import datetime
from functools import wraps
from time import time
from flask import Flask, g, render_template, send_from_directory, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "db.sqlite3"
MEDIA_FOLDER = BASE_DIR / "media"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


app = Flask(__name__)
app.config['MEDIA_FOLDER'] = MEDIA_FOLDER
app.secret_key = '39b32d04ffc4243262391cd33c680241e5e1f704b1f404562ebab93f547f787b'
ADMIN_PASSWORD_HASH = 'scrypt:32768:8:1$ppSbMms6fd2LcmlS$37c717afbc67a948074e0636dc3fcb03f1a602fc8aef895952f05a6a0e48cfba4a3330a072a47ea6d853c0fc6b21d8a39dd20140f03ae4f30f989c0fc2273ebe'
ADMIN_RATE_LIMIT_REQUESTS = 120
ADMIN_RATE_LIMIT_WINDOW = 60
LOGIN_FAILED_LIMIT = 5
LOGIN_FAILED_WINDOW = 15 * 60
_admin_rate_limits = {}
_login_failed_attempts = {}


def get_client_ip():
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.remote_addr or "unknown"


def is_rate_limited(store, key, limit, window_seconds):
    now = time()
    attempts = [timestamp for timestamp in store.get(key, []) if now - timestamp < window_seconds]
    store[key] = attempts
    return len(attempts) >= limit


def record_rate_limit_attempt(store, key, window_seconds):
    now = time()
    attempts = [timestamp for timestamp in store.get(key, []) if now - timestamp < window_seconds]
    attempts.append(now)
    store[key] = attempts


@app.before_request
def limit_admin_requests():
    if not request.path.startswith("/admin/"):
        return None
    key = get_client_ip()
    if is_rate_limited(_admin_rate_limits, key, ADMIN_RATE_LIMIT_REQUESTS, ADMIN_RATE_LIMIT_WINDOW):
        return "Too many admin requests. Please wait a minute and try again.", 429
    record_rate_limit_attempt(_admin_rate_limits, key, ADMIN_RATE_LIMIT_WINDOW)
    return None


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/admin/login/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        client_ip = get_client_ip()
        if is_rate_limited(_login_failed_attempts, client_ip, LOGIN_FAILED_LIMIT, LOGIN_FAILED_WINDOW):
            flash('Too many failed login attempts. Please wait 15 minutes and try again.', 'error')
            return render_template("admin/login.html"), 429

        password = request.form.get("password")
        if check_password_hash(ADMIN_PASSWORD_HASH, password):
            _login_failed_attempts.pop(client_ip, None)
            session['logged_in'] = True
            flash('Logged in successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            record_rate_limit_attempt(_login_failed_attempts, client_ip, LOGIN_FAILED_WINDOW)
            flash('Incorrect password!', 'error')
    return render_template("admin/login.html")


@app.route("/admin/logout/")
def logout():
    session.pop('logged_in', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))


def get_db():
    if "db" not in g:
        connection = sqlite3.connect(DATABASE)
        connection.row_factory = sqlite3.Row
        g.db = connection
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def media_url(path):
    return f"/media/{path}" if path else ""


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_file(file, subfolder):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{filename}"
        folder = app.config['MEDIA_FOLDER'] / subfolder
        folder.mkdir(parents=True, exist_ok=True)
        file.save(folder / filename)
        return f"{subfolder}/{filename}"
    return None


@app.route("/media/<path:filename>")
def media(filename):
    return send_from_directory(app.config['MEDIA_FOLDER'], filename)


def fetch_all(query, params=()):
    return [dict(row) for row in get_db().execute(query, params).fetchall()]


def fetch_one(query, params=()):
    row = get_db().execute(query, params).fetchone()
    return dict(row) if row else None


@app.route("/")
def home():
    activities = fetch_all(
        """
        select id, title, description, image, created_at
        from content_activity
        order by id
        """
    )
    slides = fetch_all(
        """
        select id, title, image, "order"
        from content_carouselimage
        order by "order", id
        """
    )

    for activity in activities:
        activity["image_url"] = media_url(activity["image"])
    for slide in slides:
        slide["image_url"] = media_url(slide["image"])

    return render_template("home.html", activities=activities, slides=slides)


@app.route("/activities/")
def activities_view():
    return render_template("activities.html")


@app.route("/about/")
def about_view():
    return render_template("about.html")


@app.route("/contact/")
def contact_view():
    contact_persons = fetch_all(
        """
        select id, name, designation, contact_no, "order"
        from content_contactperson
        order by "order", id
        """
    )
    contact_info = fetch_one(
        """
        select id, email, address, google_map_embed
        from content_contactinfo
        order by id
        limit 1
        """
    )
    contact_photos = fetch_all(
        """
        select id, image, "order", created_at
        from content_contactphoto
        order by "order", id
        limit 5
        """
    )

    for photo in contact_photos:
        photo["image_url"] = media_url(photo["image"])

    return render_template(
        "contact.html",
        contact_persons=contact_persons,
        contact_info=contact_info,
        contact_photos=contact_photos,
    )


@app.route("/donate/")
def donate_view():
    return render_template("donate.html")


# ============ ADMIN ROUTES ============
@app.route("/admin/")
@login_required
def admin_dashboard():
    # Get counts for dashboard
    db = get_db()
    activity_count = db.execute("SELECT COUNT(*) FROM content_activity").fetchone()[0]
    carousel_count = db.execute("SELECT COUNT(*) FROM content_carouselimage").fetchone()[0]
    contact_count = db.execute("SELECT COUNT(*) FROM content_contactperson").fetchone()[0]
    photo_count = db.execute("SELECT COUNT(*) FROM content_contactphoto").fetchone()[0]
    
    return render_template("admin/dashboard.html", 
                         activity_count=activity_count,
                         carousel_count=carousel_count,
                         contact_count=contact_count,
                         photo_count=photo_count)


# Activities
@app.route("/admin/activities/")
@login_required
def admin_activities():
    activities = fetch_all("SELECT id, title, description, image, created_at FROM content_activity ORDER BY id")
    for a in activities:
        a["image_url"] = media_url(a["image"])
    return render_template("admin/activities.html", activities=activities)


@app.route("/admin/activities/add/", methods=["GET", "POST"])
@login_required
def admin_add_activity():
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        file = request.files.get("image")
        image_path = save_file(file, "activities") if file else None
        
        db = get_db()
        db.execute(
            "INSERT INTO content_activity (title, description, image, created_at) VALUES (?, ?, ?, ?)",
            (title, description, image_path, datetime.now())
        )
        db.commit()
        flash("Activity added successfully!", "success")
        return redirect(url_for("admin_activities"))
    
    return render_template("admin/activity_form.html", activity=None)


@app.route("/admin/activities/<int:id>/edit/", methods=["GET", "POST"])
@login_required
def admin_edit_activity(id):
    activity = fetch_one("SELECT * FROM content_activity WHERE id = ?", (id,))
    if not activity:
        flash("Activity not found!", "error")
        return redirect(url_for("admin_activities"))
    
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        file = request.files.get("image")
        image_path = save_file(file, "activities") if file else activity["image"]
        
        db = get_db()
        db.execute(
            "UPDATE content_activity SET title = ?, description = ?, image = ? WHERE id = ?",
            (title, description, image_path, id)
        )
        db.commit()
        flash("Activity updated successfully!", "success")
        return redirect(url_for("admin_activities"))
    
    activity["image_url"] = media_url(activity["image"])
    return render_template("admin/activity_form.html", activity=activity)


@app.route("/admin/activities/<int:id>/delete/", methods=["POST"])
@login_required
def admin_delete_activity(id):
    db = get_db()
    db.execute("DELETE FROM content_activity WHERE id = ?", (id,))
    db.commit()
    flash("Activity deleted successfully!", "success")
    return redirect(url_for("admin_activities"))


# Carousel Images
@app.route("/admin/carousel/")
@login_required
def admin_carousel():
    items = fetch_all("SELECT id, title, image, \"order\" FROM content_carouselimage ORDER BY \"order\", id")
    for i in items:
        i["image_url"] = media_url(i["image"])
    return render_template("admin/carousel.html", items=items)


@app.route("/admin/carousel/add/", methods=["GET", "POST"])
@login_required
def admin_add_carousel():
    if request.method == "POST":
        title = request.form.get("title")
        order = request.form.get("order", 0)
        file = request.files.get("image")
        image_path = save_file(file, "carousel") if file else None
        
        db = get_db()
        db.execute(
            "INSERT INTO content_carouselimage (title, image, \"order\") VALUES (?, ?, ?)",
            (title, image_path, order)
        )
        db.commit()
        flash("Carousel item added successfully!", "success")
        return redirect(url_for("admin_carousel"))
    
    return render_template("admin/carousel_form.html", item=None)


@app.route("/admin/carousel/<int:id>/edit/", methods=["GET", "POST"])
@login_required
def admin_edit_carousel(id):
    item = fetch_one("SELECT * FROM content_carouselimage WHERE id = ?", (id,))
    if not item:
        flash("Carousel item not found!", "error")
        return redirect(url_for("admin_carousel"))
    
    if request.method == "POST":
        title = request.form.get("title")
        order = request.form.get("order", 0)
        file = request.files.get("image")
        image_path = save_file(file, "carousel") if file else item["image"]
        
        db = get_db()
        db.execute(
            "UPDATE content_carouselimage SET title = ?, image = ?, \"order\" = ? WHERE id = ?",
            (title, image_path, order, id)
        )
        db.commit()
        flash("Carousel item updated successfully!", "success")
        return redirect(url_for("admin_carousel"))
    
    item["image_url"] = media_url(item["image"])
    return render_template("admin/carousel_form.html", item=item)


@app.route("/admin/carousel/<int:id>/delete/", methods=["POST"])
@login_required
def admin_delete_carousel(id):
    db = get_db()
    db.execute("DELETE FROM content_carouselimage WHERE id = ?", (id,))
    db.commit()
    flash("Carousel item deleted successfully!", "success")
    return redirect(url_for("admin_carousel"))


# Contact Persons
@app.route("/admin/contact-persons/")
@login_required
def admin_contact_persons():
    persons = fetch_all("SELECT id, name, designation, contact_no, \"order\" FROM content_contactperson ORDER BY \"order\", id")
    return render_template("admin/contact_persons.html", persons=persons)


@app.route("/admin/contact-persons/add/", methods=["GET", "POST"])
@login_required
def admin_add_contact_person():
    if request.method == "POST":
        name = request.form.get("name")
        designation = request.form.get("designation")
        contact_no = request.form.get("contact_no")
        order = request.form.get("order", 0)
        
        db = get_db()
        db.execute(
            "INSERT INTO content_contactperson (name, designation, contact_no, \"order\") VALUES (?, ?, ?, ?)",
            (name, designation, contact_no, order)
        )
        db.commit()
        flash("Contact person added successfully!", "success")
        return redirect(url_for("admin_contact_persons"))
    
    return render_template("admin/contact_person_form.html", person=None)


@app.route("/admin/contact-persons/<int:id>/edit/", methods=["GET", "POST"])
@login_required
def admin_edit_contact_person(id):
    person = fetch_one("SELECT * FROM content_contactperson WHERE id = ?", (id,))
    if not person:
        flash("Contact person not found!", "error")
        return redirect(url_for("admin_contact_persons"))
    
    if request.method == "POST":
        name = request.form.get("name")
        designation = request.form.get("designation")
        contact_no = request.form.get("contact_no")
        order = request.form.get("order", 0)
        
        db = get_db()
        db.execute(
            "UPDATE content_contactperson SET name = ?, designation = ?, contact_no = ?, \"order\" = ? WHERE id = ?",
            (name, designation, contact_no, order, id)
        )
        db.commit()
        flash("Contact person updated successfully!", "success")
        return redirect(url_for("admin_contact_persons"))
    
    return render_template("admin/contact_person_form.html", person=person)


@app.route("/admin/contact-persons/<int:id>/delete/", methods=["POST"])
@login_required
def admin_delete_contact_person(id):
    db = get_db()
    db.execute("DELETE FROM content_contactperson WHERE id = ?", (id,))
    db.commit()
    flash("Contact person deleted successfully!", "success")
    return redirect(url_for("admin_contact_persons"))


# Contact Info
@app.route("/admin/contact-info/", methods=["GET", "POST"])
@login_required
def admin_contact_info():
    contact_info = fetch_one("SELECT * FROM content_contactinfo ORDER BY id LIMIT 1")
    if not contact_info:
        contact_info = {"id": None, "email": "", "address": "", "google_map_embed": ""}
    
    if request.method == "POST":
        email = request.form.get("email")
        address = request.form.get("address")
        google_map_embed = request.form.get("google_map_embed")
        
        db = get_db()
        if contact_info["id"]:
            db.execute(
                "UPDATE content_contactinfo SET email = ?, address = ?, google_map_embed = ? WHERE id = ?",
                (email, address, google_map_embed, contact_info["id"])
            )
        else:
            db.execute(
                "INSERT INTO content_contactinfo (email, address, google_map_embed) VALUES (?, ?, ?)",
                (email, address, google_map_embed)
            )
        db.commit()
        flash("Contact info updated successfully!", "success")
        return redirect(url_for("admin_contact_info"))
    
    return render_template("admin/contact_info.html", contact_info=contact_info)


# Contact Photos
@app.route("/admin/contact-photos/")
@login_required
def admin_contact_photos():
    photos = fetch_all("SELECT id, image, \"order\", created_at FROM content_contactphoto ORDER BY \"order\", id")
    for p in photos:
        p["image_url"] = media_url(p["image"])
    return render_template("admin/contact_photos.html", photos=photos)


@app.route("/admin/contact-photos/add/", methods=["GET", "POST"])
@login_required
def admin_add_contact_photo():
    if request.method == "POST":
        order = request.form.get("order", 0)
        file = request.files.get("image")
        image_path = save_file(file, "contact") if file else None
        
        db = get_db()
        db.execute(
            "INSERT INTO content_contactphoto (image, \"order\", created_at) VALUES (?, ?, ?)",
            (image_path, order, datetime.now())
        )
        db.commit()
        flash("Contact photo added successfully!", "success")
        return redirect(url_for("admin_contact_photos"))
    
    return render_template("admin/contact_photo_form.html", photo=None)


@app.route("/admin/contact-photos/<int:id>/edit/", methods=["GET", "POST"])
@login_required
def admin_edit_contact_photo(id):
    photo = fetch_one("SELECT * FROM content_contactphoto WHERE id = ?", (id,))
    if not photo:
        flash("Contact photo not found!", "error")
        return redirect(url_for("admin_contact_photos"))
    
    if request.method == "POST":
        order = request.form.get("order", 0)
        file = request.files.get("image")
        image_path = save_file(file, "contact") if file else photo["image"]
        
        db = get_db()
        db.execute(
            "UPDATE content_contactphoto SET image = ?, \"order\" = ? WHERE id = ?",
            (image_path, order, id)
        )
        db.commit()
        flash("Contact photo updated successfully!", "success")
        return redirect(url_for("admin_contact_photos"))
    
    photo["image_url"] = media_url(photo["image"])
    return render_template("admin/contact_photo_form.html", photo=photo)


@app.route("/admin/contact-photos/<int:id>/delete/", methods=["POST"])
@login_required
def admin_delete_contact_photo(id):
    db = get_db()
    db.execute("DELETE FROM content_contactphoto WHERE id = ?", (id,))
    db.commit()
    flash("Contact photo deleted successfully!", "success")
    return redirect(url_for("admin_contact_photos"))


@app.route("/blog/")
def blog_view():
    posts = fetch_all("SELECT id, title, content, featured_image, published_at FROM content_blogpost ORDER BY published_at DESC")
    for post in posts:
        post["image_url"] = media_url(post["featured_image"])
    return render_template("blog.html", posts=posts)


# Admin Blog
@app.route("/admin/blog/")
@login_required
def admin_blog():
    posts = fetch_all("SELECT id, title, content, featured_image, published_at FROM content_blogpost ORDER BY published_at DESC")
    for post in posts:
        post["image_url"] = media_url(post["featured_image"])
    return render_template("admin/blog_simple.html", posts=posts)


@app.route("/admin/blog/add/", methods=["GET", "POST"])
@login_required
def admin_add_blog():
    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        file = request.files.get("image")
        image_path = save_file(file, "blog") if file else None
        
        db = get_db()
        db.execute(
            "INSERT INTO content_blogpost (title, content, featured_image, published_at, is_published) VALUES (?, ?, ?, ?, ?)",
            (title, content, image_path, datetime.now(), True)
        )
        db.commit()
        flash("Blog post added!", "success")
        return redirect(url_for("admin_blog"))
    
    return render_template("admin/blog_form_simple.html", post=None)


@app.route("/admin/blog/<int:id>/edit/", methods=["GET", "POST"])
@login_required
def admin_edit_blog(id):
    post = fetch_one("SELECT * FROM content_blogpost WHERE id = ?", (id,))
    if not post:
        flash("Post not found!", "error")
        return redirect(url_for("admin_blog"))
    
    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        file = request.files.get("image")
        image_path = save_file(file, "blog") if file else post["featured_image"]
        
        db = get_db()
        db.execute(
            "UPDATE content_blogpost SET title = ?, content = ?, featured_image = ? WHERE id = ?",
            (title, content, image_path, id)
        )
        db.commit()
        flash("Blog post updated!", "success")
        return redirect(url_for("admin_blog"))
    
    post["image_url"] = media_url(post["featured_image"])
    return render_template("admin/blog_form_simple.html", post=post)


@app.route("/admin/blog/<int:id>/delete/", methods=["POST"])
@login_required
def admin_delete_blog(id):
    db = get_db()
    db.execute("DELETE FROM content_blogpost WHERE id = ?", (id,))
    db.commit()
    flash("Blog post deleted!", "success")
    return redirect(url_for("admin_blog"))


if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)
