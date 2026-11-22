"""Prepare, guard and publish covers and client documents."""

from dataclasses import replace

from . import (basic, document_content, document_language, document_secrets, documents, first_page,
               report, secrets, translation, validation)
from .storage import CURRENT, OUTPUT, Refusal, json_bytes, load_check


PREVIEW = f"{OUTPUT}/first-page-preview.pdf"
STEMS = ("project-document", "technical-document")
README = "README.md"
SOURCE_INPUTS = (*documents.DOCUMENTS, ".env.example", *secrets.SETTING_FILES)


def guard(data, values):
    if secrets.contains_secret_in_data(data, values):
        raise Refusal("Remove the known secret value and replace it before trying again.")


def current(project, values, *, optional=False, for_document=False):
    if optional and project.read(CURRENT) is None:
        return None, None
    raw, data = load_check(project)
    if for_document:
        document_secrets.guard_json(CURRENT, raw, values)
    else:
        guard(data, values)
    if not isinstance(data, dict):
        raise Refusal("Make check.json a JSON object.")
    validation.validate_project(data.get("project"))
    return raw, data


def check_scope(project, data, values):
    validation.validate(data, basic.basic_checks())
    scope = documents.read_scope(project, data["project"]["round"], values,
                                 guard=document_secrets.guard_line)
    validation.validate_scope(data, scope)
    return scope


def publish(project, expected, outputs, *, readme_present=None):
    # Preflight all files before writing any, and compare inputs again under the lock.
    for name in outputs:
        project.read_output(name)
    with project.writer():
        if (any(project.read(name) != raw for name, raw in expected.items())
                or (readme_present is not None and project.path(README).is_file() != readme_present)):
            raise Refusal("Read the latest check, documents and first page, then try again.")
        originals = {name: project.read_output(name) for name in outputs}
        written = []
        try:
            for name, content in outputs.items():
                if content != originals[name]:
                    project.write(name, content)
                    written.append(name)
        except (OSError, Refusal):
            for name in reversed(written):
                if originals[name] is None:
                    project.path(name).unlink()
                else:
                    project.write(name, originals[name])
            raise


def choose(project, values, args):
    raw, data = current(project, values)
    raw_choice = project.read(first_page.CHOICE)
    saved = first_page.read_choice(raw_choice)
    frame = args.frame or (saved["frame"] if saved else "register")
    base = saved if saved and frame == saved["frame"] else first_page.defaults(frame)
    if saved and frame != saved["frame"]:
        base.update({field: saved[field] for field in (*first_page.DOCUMENT_FIELDS, "credit")})
    choice = first_page.with_options(args, base)
    client = args.client.strip()
    if not client:
        raise Refusal("Enter the client name with --client.")
    data["project"].update(client=client, language=args.language)
    guard(data, values)
    guard(choice, values)
    publish(project, {CURRENT: raw, first_page.CHOICE: raw_choice},
            {first_page.CHOICE: json_bytes(choice), CURRENT: json_bytes(data)})
    print("First page and language saved.")


def renderers():
    try:
        from . import document_theme, html_document, pdf_document
    except ModuleNotFoundError as error:
        if error.name != "reportlab":
            raise
        raise Refusal("Run this command with Python 3.9 or newer and ReportLab available.") from None
    return document_theme, html_document, pdf_document


def preview_inputs(project, values):
    raw, data = current(project, values, optional=True, for_document=True)
    raw_choice = project.read(first_page.CHOICE)
    saved = first_page.read_choice(raw_choice)
    document_secrets.guard_json(first_page.CHOICE, raw_choice, values)
    expected = {name: project.read(name) for name in SOURCE_INPUTS}
    expected.update({CURRENT: raw, first_page.CHOICE: raw_choice})
    info = data["project"] if data else {}
    scope = documents.read_scope(project, info.get("round", 1), values,
                                 guard=document_secrets.guard_line)
    if data is not None:
        try:
            validation.validate(data, basic.basic_checks())
            validation.validate_scope(data, scope)
        except Refusal:
            data = {"project": info}
    return scope, data, saved, expected


def preview(project, values, args):
    scope, data, saved, expected = preview_inputs(project, values)
    options = first_page.proposals(args, saved)
    guard([choice for _, choice in options], values)
    language = args.language or scope.language
    words = document_language.load(language)
    options = [(words[label], choice) for label, choice in options]
    source = document_content.unchanged
    draft = False
    if language != scope.language:
        name = translation.filename(language)
        expected[name] = project.read(name)
        translated = translation.read(expected[name], language)
        document_secrets.guard_json(name, expected[name], values)
        source = translation.reviewed(translated, language, preview=True)
        draft = not translation.is_confirmed(translated)
    model = document_content.build(project, scope, data, options[0][1], values,
                                   language=language, source=source, preview=True)
    if draft:
        details = {**model.detail_values, "status": (words["Status"], words["Draft translation"])}
        model = replace(model, detail_values=details)
        # The page label takes no room from the content, so the draft mark cannot overflow a frame.
        options = [(f"{label} · {words['Draft translation']}", choice) for label, choice in options]
    document_theme, _, pdf_document = renderers()
    theme = document_theme.load_theme(project, values)
    rendered = pdf_document.render_preview(model, theme, options)
    publish(project, expected, {PREVIEW: rendered})
    for line in theme.notices:
        print(line)
    print("First-page preview written.")


def delivery_inputs(project, values):
    raw, data = current(project, values, for_document=True)
    # Check the input bytes again under the publication lock after rendering.
    expected = {name: project.read(name) for name in SOURCE_INPUTS}
    scope = check_scope(project, data, values)
    if not report.is_clean(data):
        raise Refusal("The current check is Not clean. Resolve the gaps in the full check first.")
    raw_choice = project.read(first_page.CHOICE)
    choice = first_page.read_choice(raw_choice)
    if choice is None:
        raise Refusal("Approve the first page and language with choose before making the document.")
    document_secrets.guard_json(first_page.CHOICE, raw_choice, values)
    language = data["project"]["language"]
    if language not in ("en", "ar", "both") or not data["project"]["client"].strip():
        raise Refusal("Save the client and language with choose before making the document.")
    if not choice["prepared_by"]:
        raise Refusal("Save the preparer with choose --prepared-by before making the document.")
    expected.update({CURRENT: raw, first_page.CHOICE: raw_choice})
    return scope, data, choice, expected


def translation_models(project, scope, data, choice, values, *, language, source):
    if choice is None:
        document_content.build(project, scope, data, first_page.defaults("register"), values,
                               language=language, source=source, preview=True)
    else:
        document_content.paired(project, scope, data, choice, values, language=language, source=source)


def translation_sources(project, scope, data, choice, values):
    sources = translation.Sources()
    translation_models(project, scope, data, choice, values, language=scope.language,
                       source=sources.collect)
    return sources.texts


def translate(project, values, language, *, confirm=False):
    if project.read(first_page.CHOICE) is None:
        scope, data, choice, expected = preview_inputs(project, values)
    else:
        scope, data, choice, expected = delivery_inputs(project, values)
    if language == scope.language:
        raise Refusal("Use the approved words directly. This language needs no translation.")
    name = translation.filename(language)
    raw = project.read(name)
    expected[name] = raw
    existing = translation.read(raw, language) if raw is not None or confirm else None
    document_secrets.guard_json(name, raw, values)
    texts = translation_sources(project, scope, data, choice, values)
    if confirm:
        source = translation.reviewed(existing, language, texts, confirm=True)
        translation_models(project, scope, data, choice, values, language=language, source=source)
        content = translation.confirmed(existing)
    else:
        content = translation.refreshed(existing, language, texts)
    guard(content, values)
    publish(project, expected, {name: json_bytes(content)})
    print("Translation confirmed." if confirm else "Translation file written.")


def document(project, values):
    scope, data, choice, expected = delivery_inputs(project, values)
    readme_present = project.path(README).is_file()
    selected = data["project"]["language"]
    languages = ("en", "ar") if selected == "both" else (selected,)
    models = {}
    for language in languages:
        source = document_content.unchanged
        if language != scope.language:
            name = translation.filename(language)
            expected[name] = project.read(name)
            translated = translation.read(expected[name], language)
            document_secrets.guard_json(name, expected[name], values)
            texts = translation_sources(project, scope, data, choice, values)
            source = translation.reviewed(translated, language, texts)
        models[language] = document_content.paired(project, scope, data, choice, values,
                                                    language=language, source=source,
                                                    readme_present=readme_present)

    document_theme, html_document, pdf_document = renderers()
    theme = document_theme.load_theme(project, values)
    outputs = {}
    for language, pair in models.items():
        suffix = "-ar" if language == "ar" else ""
        for stem, model in zip(STEMS, pair):
            pdf, page_numbers = pdf_document.render_document(model, theme)
            html = html_document.render_document(model, theme, page_numbers)
            markup = html.decode("utf-8")
            guard(markup, values)
            if language == "en" and translation.has_arabic_letters(markup):
                raise Refusal("Use English text for the English document. It contains Arabic letters.")
            guard(pdf.decode("utf-8", errors="ignore"), values)
            outputs[f"{OUTPUT}/{stem}{suffix}.pdf"] = pdf
            outputs[f"{OUTPUT}/{stem}{suffix}.html"] = html
    publish(project, expected, outputs, readme_present=readme_present)
    for line in theme.notices:
        print(line)
    print("Project and technical documents written.")
