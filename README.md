# Chakdah Natuner Khoje

A government-registered NGO website dedicated to uplifting underprivileged communities through education, healthcare, women's empowerment, and social welfare initiatives.

## Features

- **Home Page**: Hero slider, About section, Our Vision cards, Activity gallery
- **About Page**: Detailed information about the organization, mission, vision, and impact
- **Activities Page**: Photo gallery of on-ground initiatives
- **Contact Page**: Contact persons, email, address, Google Maps integration
- **Donate Page**: Donation information with bank details and payment methods
- **Blog Page**: Coming soon (with admin management)
- **Admin Panel**:
  - Manage activities (add, edit, delete)
  - Manage carousel images
  - Manage contact persons and info
  - Manage blog posts
  - Manage contact gallery photos

## Tech Stack

- **Backend**: Flask (Python web framework)
- **Database**: SQLite
- **Frontend**: HTML, Tailwind CSS, Alpine.js
- **Deployment Ready**: .gitignore, requirements.txt

## Installation

### 1. Clone or download the project

### 2. Set up a virtual environment (optional but recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

```bash
python app.py
```

The app will be running at `http://127.0.0.1:5000/`

## Project Structure

```
natuner_khoje_v2/
├── app.py                  # Main Flask application
├── db.sqlite3              # SQLite database
├── requirements.txt        # Python dependencies
├── update_contact_info.py  # Script to update contact info
├── media/                  # Directory for uploaded media files
│   ├── activities/
│   ├── carousel/
│   └── contact/
└── templates/
    ├── base.html
    ├── home.html
    ├── about.html
    ├── activities.html
    ├── contact.html
    ├── donate.html
    ├── blog.html
    └── admin/
        ├── base.html
        ├── dashboard.html
        ├── activities.html
        ├── activity_form.html
        ├── carousel.html
        ├── carousel_form.html
        ├── contact_persons.html
        ├── contact_person_form.html
        ├── contact_info.html
        ├── contact_photos.html
        ├── contact_photo_form.html
        ├── blog_simple.html
        └── blog_form_simple.html
```

## Admin Panel

Access the admin panel at: `http://127.0.0.1:5000/admin/`

From the admin you can:
- Add/edit/delete activities
- Manage homepage carousel images
- Update contact persons and information
- Add blog posts
- Manage contact page photos
- Update address and Google Maps embed

## Deployment Options

Since this is a Flask application with a SQLite database, Netlify won't work (it's for static sites). Here are great alternatives:

---

### **Vercel Deployment (Step-by-Step)**

1. **Push your code to GitHub/GitLab/Bitbucket**
2. **Sign up / log in to Vercel** at https://vercel.com/
3. **Import your project** from GitHub/GitLab
4. **Configure the project**:
   - **Root Directory**: `./`
   - **Build Command**: Leave blank (or set to `pip install -r requirements.txt`)
   - **Output Directory**: Leave blank
   - **Install Command**: `pip install -r requirements.txt` (auto-detected usually)
5. **Click Deploy**!
6. **Wait for deployment** (this takes a few minutes)
7. **Done!** Your site will be live at a `*.vercel.app` URL

**Important Notes for Vercel:**
- SQLite works for small traffic, but for production, consider PostgreSQL
- Uploaded media files won't persist across serverless function restarts
- For persistent storage, consider a service like AWS S3 or Cloudinary for media files

---

### 1. PythonAnywhere (Recommended for Beginners)
- Free tier available
- Easy to use
- Perfect for small to medium apps
- Guides available at: https://help.pythonanywhere.com/pages/Flask/

### 2. Render
- Simple deployment from Git
- Free tier available
- Supports PostgreSQL for better scalability
- https://render.com/

### 3. Railway
- Fast and modern
- Good for full-stack apps
- https://railway.app/

## Important Notes

- **SQLite Database**: Great for small scale, consider PostgreSQL/MySQL for production
- **Media Files**: Make sure the `media/` directory is writable by the server
- **Security**: Always use HTTPS in production
- **Backups**: Regularly backup your database

## About The Organization

**Chakdah Natuner Khoje** is a government-registered non-profit organization established in 2021, working tirelessly for the upliftment of underprivileged communities in West Bengal and Jharkhand. The organization is registered under the West Bengal Societies Registration Act, 1961 (Registration No. S0028930 of 2022-23) and holds a CSR1 Certificate approved by the Ministry of Corporate Affairs, Government of India.

### Key Initiatives:
- Free education for underprivileged children
- Homeopathic healthcare services
- Women empowerment and livelihood programs
- Sports development
- Rural infrastructure development

## License

This project is created for the Chakdah Natuner Khoje organization.
