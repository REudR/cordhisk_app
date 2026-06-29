def build_memory_block(metadata):
    lines = [
        f'<{k} type="memory">{v}</{k}>'
        for k, v in metadata.items()
        if v.strip()
    ]

    return (
        "=== MEMORY METADATA START ===\n"
        + "\n".join(lines)
        + "\n=== MEMORY METADATA END ===\n\n"
    )
