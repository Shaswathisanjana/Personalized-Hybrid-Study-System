# Academic provider fixture provenance

`openalex_work_projection.json` projects four bibliographic fields from the actual public OpenAlex response at https://api.openalex.org/works/W2741809807, inspected on 20 October 2026. All other fields are intentionally omitted; no abstract, authors or findings are invented for this real publication. Tests wrap this projection in an explicitly synthetic pagination envelope.

Other pagination, missing-metadata, abstract and failure cases are labelled synthetic fixtures generated in the test modules. They test response structure and recovery without pretending to be real publications. Test execution is offline and does not refetch OpenAlex.
