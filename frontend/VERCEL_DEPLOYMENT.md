# Deploying to Vercel 🚀

## Quick Deploy (Easiest Method)

### Step 1: Push to GitHub

1. **Initialize Git** (if not already done):
```bash
cd c:\Users\Dell\Documents\MLJResultsCompiler
git init
git add .
git commit -m "Initial commit with Next.js frontend"
```

2. **Create GitHub Repository**:
   - Go to https://github.com/new
   - Create a new repository (e.g., "mlj-results-compiler")
   - Don't initialize with README (we already have files)

3. **Push to GitHub**:
```bash
git remote add origin https://github.com/YOUR_USERNAME/mlj-results-compiler.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy to Vercel

1. **Go to Vercel**: https://vercel.com/
2. **Sign in** with GitHub
3. **Click "Add New Project"**
4. **Import your repository**:
   - Select "mlj-results-compiler"
   - Click "Import"

5. **Configure Project**:
   - **Framework Preset**: Next.js (auto-detected)
   - **Root Directory**: Click "Edit" → Set to `frontend`
   - **Build Command**: `npm run build` (default)
   - **Output Directory**: `.next` (default)
   - **Install Command**: `npm install` (default)

6. **Click "Deploy"**
   - Vercel will build and deploy your app
   - Takes about 1-2 minutes

7. **Done!** 🎉
   - Your app is live at: `https://your-project.vercel.app`

---

## Important Notes

### ⚠️ Python Backend Limitation

**Vercel serverless functions don't support Python script execution.**

The current API route (`/api/process`) will:
- ✅ Accept file uploads
- ✅ Validate Excel files
- ✅ Return file information
- ❌ **Cannot run Python processing**

### Solutions for Python Processing

#### Option 1: Separate Python Backend (Recommended)

Deploy Python backend to:
- **Railway**: https://railway.app/
- **Render**: https://render.com/
- **AWS Lambda**: https://aws.amazon.com/lambda/
- **Google Cloud Functions**: https://cloud.google.com/functions

Then update the API route to call that backend:

```typescript
// In route.ts
const response = await fetch('https://your-python-backend.com/process', {
  method: 'POST',
  body: formData,
});
```

#### Option 2: Convert Python to JavaScript

Rewrite Python logic using:
- `xlsx` npm package for Excel processing
- JavaScript/TypeScript for data manipulation
- Deploy entirely on Vercel

#### Option 3: Hybrid Approach (Best for Now)

1. **Use Vercel for frontend** (done!)
2. **Keep Python processing local** or on a server
3. **Update frontend to send files to your server**

---

## Vercel Configuration Files Created

### 1. `vercel.json`
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "framework": "nextjs"
}
```

### 2. `next.config.js` (Updated)
- Added `output: 'standalone'` for optimal Vercel deployment

### 3. `.env.production`
- Template for environment variables
- Add backend URL here if using separate Python backend

---

## After Deployment

### View Your Live App
```
https://your-project-name.vercel.app
```

### Custom Domain (Optional)
1. Go to Vercel Dashboard → Settings → Domains
2. Add your custom domain
3. Follow DNS instructions

### Environment Variables
1. Vercel Dashboard → Settings → Environment Variables
2. Add any secrets or API URLs
3. Redeploy to apply changes

---

## Vercel Dashboard Features

### Deployments
- Every git push triggers new deployment
- Preview deployments for branches
- Production deployment for `main` branch

### Logs
- Real-time function logs
- Error tracking
- Performance monitoring

### Analytics
- Page views
- Performance metrics
- User analytics

---

## Development Workflow

### Local Development
```bash
cd frontend
npm run dev
```

### Deploy Changes
```bash
git add .
git commit -m "Your changes"
git push
```
Vercel auto-deploys on push! ✨

### Rollback
- Go to Vercel Dashboard → Deployments
- Click previous deployment → Promote to Production

---

## Troubleshooting

### Build Fails
- Check Vercel build logs
- Ensure all dependencies in `package.json`
- Verify TypeScript has no errors

### API Route Errors
- Check function logs in Vercel Dashboard
- Verify API routes work locally first
- Check serverless function limits (10MB max)

### Root Directory Issues
- Make sure "Root Directory" is set to `frontend`
- Vercel needs to find `package.json` in root directory

### Environment Variables Missing
- Add them in Vercel Dashboard
- Prefix public variables with `NEXT_PUBLIC_`
- Redeploy after adding

---

## Cost

### Vercel Free Tier Includes:
- ✅ Unlimited deployments
- ✅ 100GB bandwidth/month
- ✅ Automatic SSL
- ✅ Preview deployments
- ✅ Analytics
- ✅ Serverless functions

**Perfect for this project!** No credit card needed.

---

## Alternative: Deploy Frontend Only

If you want to keep Python processing separate:

1. Deploy frontend to Vercel (as described)
2. Run Python backend on your local machine/server
3. Update API endpoint in code to point to your server
4. Use ngrok or similar to expose local Python backend

---

## Summary Checklist

- [ ] Push code to GitHub
- [ ] Import repo in Vercel
- [ ] Set root directory to `frontend`
- [ ] Deploy and get live URL
- [ ] Decide on Python backend solution
- [ ] Update API routes if needed
- [ ] Test live deployment
- [ ] (Optional) Add custom domain

---

**Your frontend will be live on Vercel!** 🎉

The UI will work perfectly. You'll just need to decide how to handle the Python processing backend.
