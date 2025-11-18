import streamlit as st
from datetime import datetime
import os
from storage_adapter import Client
import zipfile
import io
import re

# Storage is always available with the adapter
REPLIT_STORAGE_AVAILABLE = True

# Configuration: Set to True to enable OpenAI embedding clustering
ENABLE_CLUSTERING = False

# AI Model Selection (set one to True)
# Options: Claude (default), OpenAI (GPT-4o), Gemini (Gemini 2.0 Flash), OpenRouter (Qwen3), or Mistral (Mistral 7B)
USE_CLAUDE = True
USE_OPENAI = False
USE_GEMINI = False
USE_OPENROUTER = False
USE_MISTRAL = False

# Set environment variables for ai_processor to read
os.environ["USE_OPENAI"] = str(USE_OPENAI)
os.environ["USE_GEMINI"] = str(USE_GEMINI)
os.environ["USE_OPENROUTER"] = str(USE_OPENROUTER)
os.environ["USE_MISTRAL"] = str(USE_MISTRAL)

# Import after setting environment variables
from scraper import extract_blog_links, scrape_blog_post
from ai_processor import process_posts_batch, generate_cluster_labels
from embedding_cluster import cluster_blog_posts
from checkpoint_manager import CheckpointManager

st.set_page_config(
    page_title="Blog Post Analyzer",
    page_icon="📚",
    layout="wide"
)

st.title("📚 Blog Post Analyzer & Summarizer")
st.write("Automate your blog research workflow: scrape, categorize, and summarize blog posts using AI")

# Model Selection
with st.expander("⚙️ AI Model Settings", expanded=False):
    st.write("**Select the AI model to use for analysis:**")
    
    model_choice = st.radio(
        "AI Model",
        ["Claude Sonnet 4.5 (Default)", "Gemini 2.0 Flash", "OpenAI GPT-4o", "Qwen 2.5 72B (OpenRouter)", "Mistral 7B"],
        index=0,
        help="Choose which AI model to use for blog post analysis. Each model has different strengths and API costs."
    )
    
    # Update environment variables based on selection
    if model_choice == "Claude Sonnet 4.5 (Default)":
        os.environ["USE_OPENAI"] = "False"
        os.environ["USE_GEMINI"] = "False"
        os.environ["USE_OPENROUTER"] = "False"
        os.environ["USE_MISTRAL"] = "False"
        st.info("🤖 Using Claude Sonnet 4.5 - Requires ANTHROPIC_API_KEY environment variable")
    elif model_choice == "Gemini 2.0 Flash":
        os.environ["USE_OPENAI"] = "False"
        os.environ["USE_GEMINI"] = "True"
        os.environ["USE_OPENROUTER"] = "False"
        os.environ["USE_MISTRAL"] = "False"
        st.info("🤖 Using Gemini 2.0 Flash - Requires GEMINI_API_KEY environment variable")
    elif model_choice == "OpenAI GPT-4o":
        os.environ["USE_OPENAI"] = "True"
        os.environ["USE_GEMINI"] = "False"
        os.environ["USE_OPENROUTER"] = "False"
        os.environ["USE_MISTRAL"] = "False"
        st.info("🤖 Using OpenAI GPT-4o - Requires OPENAI_API_KEY environment variable")
    elif model_choice == "Qwen 2.5 72B (OpenRouter)":
        os.environ["USE_OPENAI"] = "False"
        os.environ["USE_GEMINI"] = "False"
        os.environ["USE_OPENROUTER"] = "True"
        os.environ["USE_MISTRAL"] = "False"
        st.info("🤖 Using Qwen 2.5 72B via OpenRouter - Requires OPENROUTER_API_KEY environment variable")
    elif model_choice == "Mistral 7B":
        os.environ["USE_OPENAI"] = "False"
        os.environ["USE_GEMINI"] = "False"
        os.environ["USE_OPENROUTER"] = "False"
        os.environ["USE_MISTRAL"] = "True"
        st.info("🤖 Using Mistral 7B - Requires MISTRAL_API_KEY environment variable")
    
    st.divider()
    st.caption("""
    **API Key Setup:**
    - **Claude**: Set `ANTHROPIC_API_KEY` or `AI_INTEGRATIONS_ANTHROPIC_API_KEY`
    - **Gemini**: Set `GEMINI_API_KEY`
    - **OpenAI**: Set `OPENAI_API_KEY`
    - **OpenRouter**: Set `OPENROUTER_API_KEY` (get it from https://openrouter.ai)
    - **Mistral**: Set `MISTRAL_API_KEY` (get it from https://console.mistral.ai)
    """)

# Initialize session state
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None
if 'markdown_content' not in st.session_state:
    st.session_state.markdown_content = None
if 'scraped_posts' not in st.session_state:
    st.session_state.scraped_posts = None
if 'cluster_data' not in st.session_state:
    st.session_state.cluster_data = None
if 'cluster_metadata' not in st.session_state:
    st.session_state.cluster_metadata = None
if 'checkpoint_manager' not in st.session_state:
    st.session_state.checkpoint_manager = CheckpointManager()
if 'current_run_id' not in st.session_state:
    st.session_state.current_run_id = None
if 'resume_checkpoint' not in st.session_state:
    st.session_state.resume_checkpoint = None

# Check for incomplete checkpoints
incomplete_checkpoints = st.session_state.checkpoint_manager.list_incomplete_checkpoints()

if incomplete_checkpoints and not st.session_state.resume_checkpoint:
    st.info("💾 **Found incomplete analysis runs!** You can resume from where you left off.")
    
    for checkpoint in incomplete_checkpoints[:3]:  # Show up to 3 most recent
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            st.write(f"**{checkpoint['url']}**")
        with col2:
            timestamp = datetime.fromisoformat(checkpoint['timestamp'])
            st.caption(f"Started: {timestamp.strftime('%Y-%m-%d %H:%M')}")
        with col3:
            if st.button(f"📥 Resume ({checkpoint['progress']})", key=f"resume_{checkpoint['run_id']}"):
                st.session_state.resume_checkpoint = checkpoint['run_id']
                st.rerun()
    
    st.divider()

url_input = st.text_input(
    "Enter the URL of the blog listing page:",
    placeholder="https://example.com/blog",
    help="Paste the URL where all blog posts are listed"
)

process_all = st.checkbox("Process ALL blog posts (may take 45-60 minutes for hundreds of posts)", value=False)

if not process_all:
    max_posts = st.slider(
        "Maximum number of posts to process:",
        min_value=1,
        max_value=100,
        value=10,
        help="Limit the number of posts to analyze (to manage processing time and costs)"
    )
else:
    max_posts = None
    st.warning("⚠️ Processing all posts will take significant time and use API credits. The process will run in batches of 2 concurrent requests.")

# Handle resume from checkpoint
if st.session_state.resume_checkpoint:
    checkpoint_data = st.session_state.checkpoint_manager.load_checkpoint(st.session_state.resume_checkpoint)
    
    if checkpoint_data:
        progress_text = f"{checkpoint_data.get('last_index', 0)}/{checkpoint_data.get('total_posts', 0)}"
        st.info(f"📥 Resuming from checkpoint: {progress_text} posts completed")
        
        # Pre-populate the URL
        url_input = checkpoint_data['url']
        
        # Set session state for resumption
        st.session_state.scraped_posts = checkpoint_data.get('scraped_links', [])
        st.session_state.current_run_id = checkpoint_data['run_id']
        
        # Trigger processing with resume flag
        process_resume = True
    else:
        st.error("Failed to load checkpoint. Starting a new analysis instead.")
        st.session_state.resume_checkpoint = None
        process_resume = False
else:
    process_resume = False

if st.button("🚀 Analyze Blog Posts", type="primary") or process_resume:
    if not url_input and not process_resume:
        st.error("Please enter a URL")
    else:
        try:
            # Initialize run_id at the start for proper scoping
            run_id = None
            
            # Handle resume vs new run
            if process_resume and st.session_state.resume_checkpoint:
                checkpoint_data = st.session_state.checkpoint_manager.load_checkpoint(st.session_state.resume_checkpoint)
                
                if not checkpoint_data:
                    st.error("Failed to load checkpoint. Please start a new analysis.")
                    st.stop()
                
                scraped_posts = checkpoint_data.get('scraped_links', [])
                existing_results = checkpoint_data.get('processed_results', [])
                start_index = checkpoint_data.get('last_index', 0)
                run_id = checkpoint_data['run_id']
                
                st.info(f"📥 Resuming from checkpoint - already processed {start_index} posts")
                
                # Clear resume flag
                st.session_state.resume_checkpoint = None
            else:
                # New run - scrape links first
                with st.spinner("Extracting blog post links..."):
                    # Allow up to 50 pages of pagination to handle blogs with 300+ posts
                    links = extract_blog_links(url_input, follow_pagination=True, max_pages=50)
                    
                    if not links:
                        st.error("No blog post links found on this page. Please check the URL.")
                        st.stop()
                    
                    st.success(f"Found {len(links)} potential blog posts")
                    
                    if max_posts:
                        links_to_process = links[:max_posts]
                        with st.expander("🔍 View extracted links", expanded=False):
                            for i, link in enumerate(links_to_process, 1):
                                st.text(f"{i}. {link['title'][:80]}")
                                st.caption(link['url'])
                    else:
                        links_to_process = links
                        st.info(f"📊 Processing all {len(links)} posts. This will take approximately {len(links) * 10 // 60} minutes.")
                    
                    links = links_to_process
                
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
                
                existing_results = []
                start_index = 0
                run_id = None
            
            # AI Processing with checkpointing
            progress_bar = st.progress(0 if not process_resume else 0.5)
            status_text = st.empty()
            
            total_posts = len(scraped_posts)
            posts_to_process = scraped_posts[start_index:]
            
            status_text.text(f"Analyzing posts with AI... ({start_index}/{total_posts} completed)")
            
            # Progress callback with checkpoint saving
            checkpoint_manager = st.session_state.checkpoint_manager
            results = list(existing_results)  # Start with existing results
            
            # Store run_id in session state for access from callback
            if not st.session_state.current_run_id and not run_id:
                st.session_state.current_run_id = None
            elif run_id:
                st.session_state.current_run_id = run_id
            
            def update_ai_progress_with_checkpoint(completed_in_batch, total_in_batch):
                actual_completed = start_index + completed_in_batch
                ai_progress = 0.5 + (actual_completed / total_posts * 0.2)
                progress_bar.progress(ai_progress)
                status_text.text(f"Analyzing posts with AI... ({actual_completed}/{total_posts} completed)")
                
                # Save checkpoint every 10 posts
                if checkpoint_manager.should_save_checkpoint(actual_completed - 1):
                    current_results = results[:actual_completed]
                    # Capture run_id from checkpoint creation and store in session state
                    current_run_id = checkpoint_manager.create_checkpoint(
                        url=url_input,
                        scraped_links=scraped_posts,
                        processed_results=current_results,
                        last_index=actual_completed,
                        total_posts=total_posts,
                        run_id=st.session_state.current_run_id
                    )
                    # Update session state with the run_id
                    st.session_state.current_run_id = current_run_id
                    status_text.text(f"💾 Checkpoint saved - {actual_completed}/{total_posts} completed")
            
            # Process remaining posts
            new_results = process_posts_batch(posts_to_process, progress_callback=update_ai_progress_with_checkpoint)
            results.extend(new_results)
            
            # Clustering section (can be enabled/disabled via ENABLE_CLUSTERING flag)
            if ENABLE_CLUSTERING:
                progress_bar.progress(0.7)
                status_text.text("🔍 Discovering topic clusters using embeddings...")
                
                try:
                    clustering_result = cluster_blog_posts(results)
                    
                    progress_bar.progress(0.85)
                    status_text.text("🏷️ Generating cluster labels...")
                    
                    cluster_metadata = generate_cluster_labels(clustering_result['clusters'])
                except ValueError as e:
                    if "OPENAI_API_KEY" in str(e):
                        st.warning("⚠️ Semantic clustering requires an OpenAI API key. Using AI categories instead.")
                        clustering_result = None
                        cluster_metadata = None
                    else:
                        raise
                except Exception as e:
                    st.warning(f"⚠️ Clustering failed: {str(e)}. Using AI categories instead.")
                    clustering_result = None
                    cluster_metadata = None
            else:
                # Clustering disabled - use AI categories only
                clustering_result = None
                cluster_metadata = None
            
            progress_bar.progress(1.0)
            status_text.text("✅ Analysis complete!")
            
            st.session_state.processed_data = results
            st.session_state.scraped_posts = scraped_posts
            st.session_state.cluster_data = clustering_result
            st.session_state.cluster_metadata = cluster_metadata
            
            domain = url_input.split('/')[2] if '/' in url_input else 'Unknown'
            
            if clustering_result and cluster_metadata:
                clusters = clustering_result['clusters']
                metadata = cluster_metadata
                
                markdown_lines = [
                    f"# Knowledge Base: {domain} Blog Content",
                    f"",
                    f"## Context",
                    f"This document contains curated summaries and insights from blog posts published on {domain}.",
                    f"Posts are automatically organized by topic using AI-powered semantic clustering.",
                    f"",
                    f"Use this knowledge base to:",
                    f"- Understand key topics and trends discussed in their content",
                    f"- Reference specific examples and implementations",
                    f"- Generate ideas based on established patterns and approaches",
                    f"- Support brainstorming with real-world case studies",
                    f"",
                    f"**Source URL:** {url_input}",
                    f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d')}",
                    f"**Total Articles:** {len(results)}",
                    f"**Topic Clusters Discovered:** {len(clusters)}",
                    f"",
                    f"---",
                    f"",
                    f"## Table of Contents",
                    f""
                ]
                
                for cluster_id in sorted(clusters.keys()):
                    meta = metadata.get(cluster_id, {})
                    label = meta.get('label', f'Topic {cluster_id + 1}')
                    post_count = len(clusters[cluster_id])
                    anchor = label.lower().replace(' ', '-').replace('/', '').replace('&', '')
                    markdown_lines.append(f"{cluster_id + 1}. [{label}](#{anchor}) ({post_count} articles)")
                
                markdown_lines.extend([
                    f"",
                    f"---",
                    f""
                ])
                
                for cluster_id in sorted(clusters.keys()):
                    posts = clusters[cluster_id]
                    meta = metadata.get(cluster_id, {})
                    label = meta.get('label', f'Topic {cluster_id + 1}')
                    summary = meta.get('summary', 'A group of related posts')
                    themes = meta.get('themes', [])
                    
                    markdown_lines.append(f"## {label}")
                    markdown_lines.append("")
                    markdown_lines.append(f"**Topic Overview:** {summary}")
                    if themes:
                        markdown_lines.append(f"")
                        markdown_lines.append(f"**Key Themes:** {', '.join(themes)}")
                    markdown_lines.append("")
                    markdown_lines.append(f"*{len(posts)} article{'s' if len(posts) != 1 else ''} in this cluster*")
                    markdown_lines.append("")
                    markdown_lines.append("---")
                    markdown_lines.append("")
                    
                    for idx, post in enumerate(posts, 1):
                        markdown_lines.append(f"### {idx}. {post['title']}")
                        markdown_lines.append("")
                        markdown_lines.append(f"**Source:** [{post['title']}]({post['url']})")
                        markdown_lines.append("")
                        markdown_lines.append(f"**Category:** {post.get('category', 'Other')}")
                        markdown_lines.append("")
                        
                        markdown_lines.append(f"#### Summary")
                        markdown_lines.append(post['summary'])
                        markdown_lines.append("")
                        
                        if post.get('main_points'):
                            markdown_lines.append("#### Key Takeaways")
                            for point in post['main_points']:
                                markdown_lines.append(f"- {point}")
                            markdown_lines.append("")
                        
                        if post.get('examples') and any(post['examples']):
                            markdown_lines.append("#### Real-World Examples")
                            for example in post['examples']:
                                if example:
                                    markdown_lines.append(f"- {example}")
                            markdown_lines.append("")
                        
                        if post.get('central_takeaways') and any(post['central_takeaways']):
                            markdown_lines.append("#### 💡 Central Takeaways")
                            for takeaway in post['central_takeaways']:
                                if takeaway:
                                    markdown_lines.append(f"- {takeaway}")
                            markdown_lines.append("")
                        
                        if post.get('contrarian_takeaways') and any(post['contrarian_takeaways']):
                            markdown_lines.append("#### 🔄 Contrarian Insights")
                            for takeaway in post['contrarian_takeaways']:
                                if takeaway:
                                    markdown_lines.append(f"- {takeaway}")
                            markdown_lines.append("")
                        
                        if post.get('unstated_assumptions') and any(post['unstated_assumptions']):
                            markdown_lines.append("#### 🤔 Unstated Assumptions")
                            for assumption in post['unstated_assumptions']:
                                if assumption:
                                    markdown_lines.append(f"- {assumption}")
                            markdown_lines.append("")
                        
                        if post.get('potential_experiments') and any(post['potential_experiments']):
                            markdown_lines.append("#### 🧪 Potential Experiments")
                            for experiment in post['potential_experiments']:
                                if experiment:
                                    markdown_lines.append(f"- {experiment}")
                            markdown_lines.append("")
                        
                        if post.get('industry_applications') and any(post['industry_applications']):
                            markdown_lines.append("#### 🏭 Industry Applications")
                            for application in post['industry_applications']:
                                if application:
                                    markdown_lines.append(f"- {application}")
                            markdown_lines.append("")
                        
                        markdown_lines.append("")
            else:
                categories = {}
                for result in results:
                    cat = result.get('category', 'Other')
                    if cat not in categories:
                        categories[cat] = []
                    categories[cat].append(result)
                
                markdown_lines = [
                    f"# Knowledge Base: {domain} Blog Content",
                    f"",
                    f"## Context",
                    f"This document contains curated summaries and insights from blog posts published on {domain}.",
                    f"Use this knowledge base to:",
                    f"- Understand key topics and trends discussed in their content",
                    f"- Reference specific examples and implementations",
                    f"- Generate ideas based on established patterns and approaches",
                    f"- Support brainstorming with real-world case studies",
                    f"",
                    f"**Source URL:** {url_input}",
                    f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d')}",
                    f"**Total Articles:** {len(results)}",
                    f"**Categories Covered:** {len(categories)}",
                    f"",
                    f"---",
                    f"",
                    f"## Table of Contents",
                    f""
                ]
                
                for i, category in enumerate(sorted(categories.keys()), 1):
                    post_count = len(categories[category])
                    markdown_lines.append(f"{i}. [{category}](#{category.lower().replace(' ', '-').replace('/', '')}) ({post_count} articles)")
                
                markdown_lines.extend([
                    f"",
                    f"---",
                    f""
                ])
                
                for category in sorted(categories.keys()):
                    posts = categories[category]
                    markdown_lines.append(f"## {category}")
                    markdown_lines.append("")
                    markdown_lines.append(f"*{len(posts)} article{'s' if len(posts) != 1 else ''} in this category*")
                    markdown_lines.append("")
                    
                    for idx, post in enumerate(posts, 1):
                        markdown_lines.append(f"### {idx}. {post['title']}")
                        markdown_lines.append("")
                        markdown_lines.append(f"**Source:** [{post['title']}]({post['url']})")
                        markdown_lines.append("")
                        
                        markdown_lines.append(f"#### Summary")
                        markdown_lines.append(post['summary'])
                        markdown_lines.append("")
                        
                        if post.get('main_points'):
                            markdown_lines.append("#### Key Takeaways")
                            for point in post['main_points']:
                                markdown_lines.append(f"- {point}")
                            markdown_lines.append("")
                        
                        if post.get('examples') and any(post['examples']):
                            markdown_lines.append("#### Real-World Examples")
                            for example in post['examples']:
                                if example:
                                    markdown_lines.append(f"- {example}")
                            markdown_lines.append("")
                        
                        if post.get('central_takeaways') and any(post['central_takeaways']):
                            markdown_lines.append("#### 💡 Central Takeaways")
                            for takeaway in post['central_takeaways']:
                                if takeaway:
                                    markdown_lines.append(f"- {takeaway}")
                            markdown_lines.append("")
                        
                        if post.get('contrarian_takeaways') and any(post['contrarian_takeaways']):
                            markdown_lines.append("#### 🔄 Contrarian Insights")
                            for takeaway in post['contrarian_takeaways']:
                                if takeaway:
                                    markdown_lines.append(f"- {takeaway}")
                            markdown_lines.append("")
                        
                        if post.get('unstated_assumptions') and any(post['unstated_assumptions']):
                            markdown_lines.append("#### 🤔 Unstated Assumptions")
                            for assumption in post['unstated_assumptions']:
                                if assumption:
                                    markdown_lines.append(f"- {assumption}")
                            markdown_lines.append("")
                        
                        if post.get('potential_experiments') and any(post['potential_experiments']):
                            markdown_lines.append("#### 🧪 Potential Experiments")
                            for experiment in post['potential_experiments']:
                                if experiment:
                                    markdown_lines.append(f"- {experiment}")
                            markdown_lines.append("")
                        
                        if post.get('industry_applications') and any(post['industry_applications']):
                            markdown_lines.append("#### 🏭 Industry Applications")
                            for application in post['industry_applications']:
                                if application:
                                    markdown_lines.append(f"- {application}")
                            markdown_lines.append("")
                        
                        markdown_lines.append("")
            
            st.session_state.markdown_content = "\n".join(markdown_lines)
            
            # Save to Object Storage with descriptive filename
            if REPLIT_STORAGE_AVAILABLE:
                try:
                    storage_client = Client()
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    
                    # Extract blog name from domain
                    blog_name = domain.replace('.', '_').replace('-', '_')
                    post_count = len(results)
                    
                    filename = f"{timestamp}_{blog_name}_{post_count}posts.md"
                    st.session_state.last_filename = filename
                    
                    storage_client.upload_from_text(filename, st.session_state.markdown_content)
                    
                    # Mark checkpoint as complete if there was one
                    if st.session_state.current_run_id:
                        checkpoint_manager.mark_complete(st.session_state.current_run_id)
                        # Clean up old completed checkpoints (keep only last 7 days)
                        checkpoint_manager.cleanup_old_checkpoints(max_age_days=7)
                        # Clear run_id to keep session state tidy
                        st.session_state.current_run_id = None
                    
                    st.success(f"🎉 Successfully processed {len(results)} blog posts!")
                    st.info(f"📁 File saved: {filename}")
                except Exception as e:
                    # Still mark checkpoint complete even if storage fails
                    if st.session_state.current_run_id:
                        checkpoint_manager.mark_complete(st.session_state.current_run_id)
                        st.session_state.current_run_id = None
                    
                    st.success(f"🎉 Successfully processed {len(results)} blog posts!")
                    st.warning(f"⚠️ Could not save to persistent storage: {str(e)}")
            else:
                st.success(f"🎉 Successfully processed {len(results)} blog posts!")
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            
            # Save partial results if processing failed
            results_var = locals().get('results', [])
            total_posts_var = locals().get('total_posts', 'unknown')
            
            if results_var:
                try:
                    st.warning(f"💾 Saving partial results ({len(results_var)} posts processed)...")
                    
                    # Create a partial markdown
                    partial_markdown = f"# Partial Analysis\n\n**Partial results - processing interrupted**\n\n"
                    partial_markdown += f"**Processed {len(results_var)} of {total_posts_var} posts**\n\n"
                    
                    # Simple category-based organization for partial results
                    categories = {}
                    for result in results_var:
                        cat = result.get('category', 'Other')
                        if cat not in categories:
                            categories[cat] = []
                        categories[cat].append(result)
                    
                    for category in sorted(categories.keys()):
                        partial_markdown += f"\n## {category}\n\n"
                        for post in categories[category]:
                            partial_markdown += f"### {post['title']}\n\n"
                            partial_markdown += f"**Source:** {post['url']}\n\n"
                            partial_markdown += f"{post.get('summary', 'No summary available')}\n\n"
                    
                    # Try to save partial results
                    if REPLIT_STORAGE_AVAILABLE:
                        storage_client = Client()
                        partial_filename = f"PARTIAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                        storage_client.upload_from_text(partial_filename, partial_markdown)
                        
                        st.info(f"💾 Partial results saved as: {partial_filename}")
                        st.info("You can resume this analysis from the incomplete checkpoint shown at the top of the page.")
                    else:
                        st.info("💾 Partial results available for download below")
                except Exception as save_error:
                    st.error(f"Could not save partial results: {save_error}")

if st.session_state.processed_data:
    st.header("📊 Results")
    
    results = st.session_state.processed_data
    
    view_mode = st.radio(
        "View by:",
        ["🎯 Topic Clusters (AI-Discovered)", "📂 AI Categories"],
        horizontal=True,
        help="Topic Clusters are automatically discovered using semantic similarity, while AI Categories are assigned by the AI"
    )
    
    if view_mode == "🎯 Topic Clusters (AI-Discovered)" and st.session_state.cluster_data:
        clusters = st.session_state.cluster_data['clusters']
        metadata = st.session_state.cluster_metadata or {}
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Posts", len(results))
        with col2:
            st.metric("Topic Clusters", len(clusters))
        with col3:
            st.metric("Ready to Export", "✓")
        
        st.info("🧠 **Semantic Clustering**: Posts are grouped by content similarity using AI embeddings, not predefined categories. This reveals natural topic patterns.")
        
        for cluster_id in sorted(clusters.keys()):
            posts = clusters[cluster_id]
            meta = metadata.get(cluster_id, {}) if metadata else {}
            label = meta.get('label', f'Topic {cluster_id + 1}')
            summary = meta.get('summary', 'A group of related posts')
            themes = meta.get('themes', [])
            
            with st.expander(f"🎯 {label} ({len(posts)} posts)", expanded=False):
                st.markdown(f"**Cluster Summary:** {summary}")
                if themes:
                    st.markdown(f"**Key Themes:** {', '.join(themes)}")
                st.divider()
                
                for post in posts:
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
                    
                    with st.expander("💡 Deep Insights for Brainstorming"):
                        if post.get('central_takeaways') and any(post['central_takeaways']):
                            st.markdown("**💡 Central Takeaways:**")
                            for takeaway in post['central_takeaways']:
                                if takeaway:
                                    st.markdown(f"- {takeaway}")
                            st.write("")
                        
                        if post.get('contrarian_takeaways') and any(post['contrarian_takeaways']):
                            st.markdown("**🔄 Contrarian Insights:**")
                            for takeaway in post['contrarian_takeaways']:
                                if takeaway:
                                    st.markdown(f"- {takeaway}")
                            st.write("")
                        
                        if post.get('unstated_assumptions') and any(post['unstated_assumptions']):
                            st.markdown("**🤔 Unstated Assumptions:**")
                            for assumption in post['unstated_assumptions']:
                                if assumption:
                                    st.markdown(f"- {assumption}")
                            st.write("")
                        
                        if post.get('potential_experiments') and any(post['potential_experiments']):
                            st.markdown("**🧪 Potential Experiments:**")
                            for experiment in post['potential_experiments']:
                                if experiment:
                                    st.markdown(f"- {experiment}")
                            st.write("")
                        
                        if post.get('industry_applications') and any(post['industry_applications']):
                            st.markdown("**🏭 Industry Applications:**")
                            for application in post['industry_applications']:
                                if application:
                                    st.markdown(f"- {application}")
                    
                    st.divider()
    else:
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
                    
                    with st.expander("💡 Deep Insights for Brainstorming"):
                        if post.get('central_takeaways') and any(post['central_takeaways']):
                            st.markdown("**💡 Central Takeaways:**")
                            for takeaway in post['central_takeaways']:
                                if takeaway:
                                    st.markdown(f"- {takeaway}")
                            st.write("")
                        
                        if post.get('contrarian_takeaways') and any(post['contrarian_takeaways']):
                            st.markdown("**🔄 Contrarian Insights:**")
                            for takeaway in post['contrarian_takeaways']:
                                if takeaway:
                                    st.markdown(f"- {takeaway}")
                            st.write("")
                        
                        if post.get('unstated_assumptions') and any(post['unstated_assumptions']):
                            st.markdown("**🤔 Unstated Assumptions:**")
                            for assumption in post['unstated_assumptions']:
                                if assumption:
                                    st.markdown(f"- {assumption}")
                            st.write("")
                        
                        if post.get('potential_experiments') and any(post['potential_experiments']):
                            st.markdown("**🧪 Potential Experiments:**")
                            for experiment in post['potential_experiments']:
                                if experiment:
                                    st.markdown(f"- {experiment}")
                            st.write("")
                        
                        if post.get('industry_applications') and any(post['industry_applications']):
                            st.markdown("**🏭 Industry Applications:**")
                            for application in post['industry_applications']:
                                if application:
                                    st.markdown(f"- {application}")
                    
                    st.divider()
    
    st.header("💾 Export")
    
    if st.session_state.markdown_content:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"blog_analysis_{timestamp}.md"
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                label="📄 Download Analysis Summary (Markdown)",
                data=st.session_state.markdown_content,
                file_name=filename,
                mime="text/markdown",
                type="primary",
                help="Download the AI-generated summary with categories and key takeaways"
            )
        
        with col2:
            if st.session_state.scraped_posts:
                def create_full_content_zip():
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        for i, post in enumerate(st.session_state.scraped_posts, 1):
                            safe_title = re.sub(r'[^\w\s-]', '', post['title'])
                            safe_title = re.sub(r'[-\s]+', '-', safe_title)
                            safe_title = safe_title[:50]
                            
                            markdown_content = f"""# {post['title']}

**Source:** {post['url']}

---

{post['content']}
"""
                            
                            filename = f"{i:03d}_{safe_title}.md"
                            zip_file.writestr(filename, markdown_content)
                    
                    zip_buffer.seek(0)
                    return zip_buffer.getvalue()
                
                zip_data = create_full_content_zip()
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                zip_filename = f"blog_full_content_{timestamp}.zip"
                
                st.download_button(
                    label="📦 Download Full Content (ZIP)",
                    data=zip_data,
                    file_name=zip_filename,
                    mime="application/zip",
                    type="secondary",
                    help="Download all blog posts as individual markdown files in a ZIP"
                )
        
        st.info("""
        💡 **Two download options:**
        
        **1. Analysis Summary (Markdown)**
        - Structured knowledge base with AI-generated summaries
        - Organized by categories with key takeaways and examples
        - Best for quick reference and brainstorming in ChatGPT/Claude Projects
        
        **2. Full Content (ZIP)**
        - Complete original content of each blog post as individual markdown files
        - Preserves full text from each article
        - Best for deep research, archival, or detailed content analysis
        
        **How to use in ChatGPT Projects or Claude:**
        1. Upload the Analysis Summary markdown file to your project
        2. The AI will use it as context for all conversations
        3. For deeper dives, reference the full content files
        """)
        
        with st.expander("📄 Preview Markdown Output"):
            st.code(st.session_state.markdown_content, language="markdown")

st.divider()

# Show saved files from Object Storage
if REPLIT_STORAGE_AVAILABLE:
    st.header("📂 Saved Analysis Files")
    st.write("All previously analyzed blog reports are saved here for easy access across sessions.")

    try:
        storage_client = Client()
        saved_files = [f.name for f in storage_client.list()]
        
        if saved_files:
            # Sort files by timestamp (newest first)
            saved_files.sort(reverse=True)
            
            st.success(f"📦 {len(saved_files)} saved analysis file(s) available")
            
            for file in saved_files:
                # Parse filename to show readable info
                try:
                    parts = file.replace('.md', '').split('_')
                    if len(parts) >= 3:
                        timestamp_str = parts[0]
                        # Format: YYYYMMDD_HHMMSS -> YYYY-MM-DD HH:MM:SS
                        if len(timestamp_str) == 14:
                            date_part = f"{timestamp_str[:4]}-{timestamp_str[4:6]}-{timestamp_str[6:8]}"
                            time_part = f"{timestamp_str[8:10]}:{timestamp_str[10:12]}:{timestamp_str[12:14]}"
                            readable_date = f"{date_part} {time_part}"
                        else:
                            readable_date = timestamp_str
                        
                        blog_name = ' '.join(parts[1:-1]).replace('_', '.')
                        post_info = parts[-1]
                        
                        display_name = f"📄 {readable_date} - {blog_name} ({post_info})"
                    else:
                        display_name = f"📄 {file}"
                except:
                    display_name = f"📄 {file}"
                
                # Create download button for each file with error handling
                try:
                    content = storage_client.download_as_text(file)
                    st.download_button(
                        label=display_name,
                        data=content,
                        file_name=file,
                        mime="text/markdown",
                        key=f"download_{file}",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"❌ Could not load {file}: {str(e)}")
        else:
            st.info("No saved files yet. Run an analysis to create your first file!")
            
    except Exception as e:
        st.warning(f"⚠️ Storage unavailable: {str(e)}")
        st.info("💡 Files from the current session are available in the Export section above.")

st.divider()
st.caption("Built with Streamlit • Powered by Claude AI, Gemini AI, OpenAI, OpenRouter, or Mistral AI (configurable)")
