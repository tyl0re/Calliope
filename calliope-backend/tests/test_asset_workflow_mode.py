from calliope.agent.asset_agent import _workflow_matches_krea_mode


def test_krea_workflow_mode_matching_handles_imported_filenames():
    assert _workflow_matches_krea_mode(
        "krea2_character_sheet_local_fp8_uncensored_API", "local"
    )
    assert not _workflow_matches_krea_mode(
        "krea2_character_sheet_local_fp8_uncensored_API", "api"
    )
    assert _workflow_matches_krea_mode("krea2_character_sheet_api", "api")
