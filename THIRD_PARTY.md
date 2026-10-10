# Third-party notices

The bundled `src/ttree/data/o200k_base.tiktoken` vocabulary and the splitting
pattern in `src/ttree/tokenizer.py` come from OpenAI's MIT-licensed
[tiktoken](https://github.com/openai/tiktoken).
The full license is included in `src/ttree/data/TIKTOKEN_LICENSE` and ships in
the wheel. The vocabulary is from
https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken.
Its SHA-256 is
`446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`.

Other dependencies retain their own license notices in their distributions.
The offline artifact includes the complete dependency wheels, with those notices.

Legacy Word text extraction uses the small pure-Python
[olefile](https://github.com/decalage2/olefile) dependency. Its license remains in
its installed wheel. The piece-table reader follows Microsoft's public
[MS-DOC text retrieval specification](https://learn.microsoft.com/en-us/openspecs/office_file_formats/ms-doc/01d5d8c4-cf9c-4ef9-80fd-439e763cfe01)
and linked FIB, Clx and FcCompressed definitions. It never invokes an Office runtime.
