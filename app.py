import streamlit as st
from scraper import extract_blog_links, scrape_blog_post
from ai_processor import process_posts_batch
from datetime import datetime
import os
from replit.object_storage import Client

st.set_page_config(
    page_title="Blog Post Analyzer",
    page_icon="📚",
    layout="wide"
)

st.title("📚 Blog Post Analyzer & Summarizer")
st.write("Automate your blog research workflow: scrape, categorize, and summarize blog posts using AI")

if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None
if 'markdown_content' not in st.session_state:
    st.session_state.markdown_content = None

url_input = st.text_input(
    "Enter the URL of the blog listing page:",
    placeholder="https://example.com/blog",
    help="Paste the URL where all blog posts are listed"
)

max_posts = st.slider(
    "Maximum number of posts to process:",
    min_value=5,
    max_value=50,
    value=10,
    help="Limit the number of posts to analyze (to manage processing time and costs)"
)

if st.button("🚀 Analyze Blog Posts", type="primary"):
    if not url_input:
        st.error("Please enter a URL")
    else:
        try:
            with st.spinner("Extracting blog post links..."):
                links = extract_blog_links(url_input)
                
                if not links:
                    st.error("No blog post links found on this page. Please check the URL.")
                    st.stop()
                
                st.success(f"Found {len(links)} potential blog posts")
                
                with st.expander("🔍 View extracted links", expanded=False):
                    for i, link in enumerate(links[:max_posts], 1):
                        st.text(f"{i}. {link['title'][:80]}")
                        st.caption(link['url'])
                
                links = links[:max_posts]
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            scraped_posts = []
            scraping_errors = []
            status_text.text(f"Scraping content from {len(links)} posts...")
            
            for i, link in enumerate(links):
                try:
                    post = scrape_blog_post(link['url'])
                    post['title'] = link['title']
                    if len(post['content']) > 100:
                        scraped_posts.append(post)
                    else:
                        scraping_errors.append(f"{link['title'][:50]}: Content too short")
                    progress_bar.progress((i + 1) / len(links) * 0.5)
                except Exception as e:
                    scraping_errors.append(f"{link['title'][:50]}: {str(e)}")
            
            if scraping_errors:
                with st.expander(f"⚠️ Skipped {len(scraping_errors)} posts (click to see details)"):
                    for error in scraping_errors[:10]:
                        st.text(error)
            
            if not scraped_posts:
                st.error("No content could be scraped from the posts. The page might not contain standard blog post links.")
                st.info("💡 Try providing a different URL or a page that lists blog articles more clearly.")
                st.stop()
            
            status_text.text(f"Analyzing {len(scraped_posts)} posts with AI...")
            
            def update_progress(current, total):
                progress_bar.progress(0.5 + (current / total) * 0.5)
                status_text.text(f"Analyzing posts with AI... {current}/{total}")
            
            results = process_posts_batch(scraped_posts, progress_callback=update_progress)
            
            progress_bar.progress(1.0)
            status_text.text("✅ Analysis complete!")
            
            st.session_state.processed_data = results
            
            categories = {}
            for result in results:
                cat = result.get('category', 'Other')
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(result)
            
            markdown_lines = [
                f"# Blog Post Analysis",
                f"",
                f"**Source:** {url_input}",
                f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                f"**Total Posts Analyzed:** {len(results)}",
                f"",
                f"---",
                f""
            ]
            
            for category in sorted(categories.keys()):
                posts = categories[category]
                markdown_lines.append(f"## 📂 {category} ({len(posts)} posts)")
                markdown_lines.append("")
                
                for post in posts:
                    markdown_lines.append(f"### {post['title']}")
                    markdown_lines.append(f"**URL:** {post['url']}")
                    markdown_lines.append("")
                    markdown_lines.append(f"**Summary:**")
                    markdown_lines.append(post['summary'])
                    markdown_lines.append("")
                    
                    if post.get('main_points'):
                        markdown_lines.append("**Main Points:**")
                        for point in post['main_points']:
                            markdown_lines.append(f"- {point}")
                        markdown_lines.append("")
                    
                    if post.get('examples') and any(post['examples']):
                        markdown_lines.append("**Examples:**")
                        for example in post['examples']:
                            if example:
                                markdown_lines.append(f"- {example}")
                        markdown_lines.append("")
                    
                    markdown_lines.append("---")
                    markdown_lines.append("")
            
            st.session_state.markdown_content = "\n".join(markdown_lines)
            
            # Save to Object Storage
            try:
                storage_client = Client()
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"blog_analysis_{timestamp}.md"
                storage_client.upload_from_text(filename, st.session_state.markdown_content)
                st.success(f"🎉 Successfully processed {len(results)} blog posts!")
                st.info(f"📁 Output saved to Object Storage: {filename}")
            except Exception as e:
                st.success(f"🎉 Successfully processed {len(results)} blog posts!")
                st.warning(f"Note: Could not save to Object Storage: {str(e)}")
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

if st.session_state.processed_data:
    st.header("📊 Results")
    
    results = st.session_state.processed_data
    categories = {}
    for result in results:
        cat = result.get('category', 'Other')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(result)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Posts", len(results))
    with col2:
        st.metric("Categories", len(categories))
    with col3:
        st.metric("Ready to Export", "✓")
    
    for category in sorted(categories.keys()):
        with st.expander(f"📂 {category} ({len(categories[category])} posts)", expanded=False):
            for post in categories[category]:
                st.markdown(f"**{post['title']}**")
                st.caption(post['url'])
                st.write(post['summary'])
                
                if post.get('main_points'):
                    st.markdown("**Main Points:**")
                    for point in post['main_points']:
                        st.markdown(f"- {point}")
                
                if post.get('examples') and any(post['examples']):
                    st.markdown("**Examples:**")
                    for example in post['examples']:
                        if example:
                            st.markdown(f"- {example}")
                
                st.divider()
    
    st.header("💾 Export")
    
    if st.session_state.markdown_content:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"blog_analysis_{timestamp}.md"
        
        st.download_button(
            label="⬇️ Download Markdown File",
            data=st.session_state.markdown_content,
            file_name=filename,
            mime="text/markdown",
            type="primary"
        )
        
        st.info("💡 You can upload this markdown file to ChatGPT Projects or Claude to use as context for brainstorming sessions.")
        
        with st.expander("📄 Preview Markdown Output"):
            st.code(st.session_state.markdown_content, language="markdown")

st.divider()

# Show saved files from Object Storage
st.header("📂 Saved Analysis Files")
try:
    storage_client = Client()
    saved_files = storage_client.list()
    
    if saved_files:
        st.write(f"Found {len(saved_files)} saved analysis file(s):")
        for file in saved_files:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.text(file)
            with col2:
                if st.button("Download", key=f"dl_{file}"):
                    content = storage_client.download_as_text(file)
                    st.download_button(
                        label="⬇️ Save File",
                        data=content,
                        file_name=file,
                        mime="text/markdown",
                        key=f"save_{file}"
                    )
    else:
        st.info("No saved files yet. Run an analysis to create your first file!")
except Exception as e:
    st.info("Object Storage not configured. Files will only be available for download during the session.")

st.divider()
st.caption("Built with Streamlit • Powered by Claude AI via Replit AI Integrations")
