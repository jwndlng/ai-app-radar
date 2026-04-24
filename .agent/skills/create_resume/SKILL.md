---
name: create_resume
description: Create a new tailored resume variant based on the template
---
# Create Resume Skill

When requested to create a new customized resume for a specific job or company, follow these steps exactly. This will significantly speed up the creation process and maintain consistency.

1. **Verify Target Role and Company**
   Ensure you know the target role (e.g., `security_engineer`, `swe_observability`) and the company name.

2. **Copy the Base Template**
   Create a discrete copy of the template directory. For example, if the role is for a senior SWE, the folder could be called `resume_senior_swe`.
   // turbo
   `cp -r resume_TPL resume_<role_or_company>`

3. **Incorporate External References**
   Search the external Obsidian vault for company-specific interview prep, job descriptions, or application notes to gain context.
   Path: `/Users/jan/Library/Mobile Documents/iCloud~md~obsidian/Documents/Notes/03 Professional/Applications`
   *Use `list_dir` and `view_file` to read the context.*

4. **Tailor the Content**
   Modify `main.tex` and `sidebar.tex` within the new directory.
   - Adjust the tagline and intro based on the target role.
   - Highlight and re-order bullet points in experience that match the job description.
   - Ensure you follow Jan's preference for structured, modular, SWE-style coding patterns and technical emphasis.

5. **Draft Cover Letter (If Applicable)**
   Create a plain text file specifically for the cover letter inside the new directory (e.g., `resume_<role>/cover_letter_<company>.txt`). 
   - Write grounded, factual text focusing on engineering and security.
   - **Crucial Rule:** Do NOT use clausal em-dashes / en-dashes (`—`) to connect sentences. Instead, break them into separate sentences. (Hyphenated compound technical words like `LLM-driven` or `Rust-based` are perfectly fine).

6. **Compile the Resume**
   Navigate into the specific resume directory and run the LuaLaTeX compiler to generate the PDF.
   // turbo
   `cd resume_<role_or_company> && lualatex main.tex`
