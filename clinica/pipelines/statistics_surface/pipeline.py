from typing import List

from clinica.pipelines.engine import GroupPipeline


class StatisticsSurface(GroupPipeline):
    """StatisticsSurface - Surface-based mass-univariate analysis with BrainStat.

    See documentation at https://aramislab.paris.inria.fr/clinica/docs/public/latest/Pipelines/Stats_Surface/

    Notes
    -----
    The `tsv_file` attribute is overloaded for this pipeline. It must contain a list of subjects
    with their sessions and all the covariates and factors needed for the GLM.

    Pipeline parameters are explained in StatisticsSurfaceCLI.define_options()
    """

    def _check_pipeline_parameters(self) -> None:
        """Check pipeline parameters."""
        from clinica.utils.exceptions import ClinicaException

        from ._utils import get_pet_surface_custom_file, get_t1_freesurfer_custom_file
        from .surfstat import get_t1_freesurfer_custom_file_template

        for compulsory_parameter_name in ("orig_input_data", "contrast"):
            if compulsory_parameter_name not in self.parameters:
                raise KeyError(
                    f"Missing compulsory parameter {compulsory_parameter_name}."
                )
        self.parameters.setdefault("covariates", None)
        self.parameters.setdefault("full_width_at_half_maximum", 20)
        self.parameters.setdefault("acq_label", None)
        self.parameters.setdefault("suvr_reference_region", None)
        self.parameters.setdefault(
            "custom_file",
            get_t1_freesurfer_custom_file_template(self.caps_directory / "subjects"),
        )
        self.parameters.setdefault("measure_label", "ct")
        self.parameters.setdefault("cluster_threshold", 0.001)
        self.parameters.setdefault("glm_type", None)

        if self.parameters["orig_input_data"] == "pet-surface":
            if not self.parameters["acq_label"]:
                raise ClinicaException(
                    "You selected pet-surface pipeline without providing the acq_label "
                    "(by setting the --acq_label option). Clinica will now exit."
                )
            if not self.parameters["suvr_reference_region"]:
                raise ClinicaException(
                    "You selected pet-surface pipeline without providing the suvr "
                    "reference region (by setting the --suvr_reference_region option). "
                    "Clinica will now exit."
                )
        if self.parameters["glm_type"] not in ("group_comparison", "correlation"):
            raise ClinicaException(
                f"The glm_type you specified is wrong: it should be group_comparison or "
                f"correlation (given value: {self.parameters['glm_type']})."
            )
        if (
            self.parameters["cluster_threshold"] < 0
            or self.parameters["cluster_threshold"] > 1
        ):
            raise ClinicaException(
                f"Cluster threshold should be between 0 and 1 "
                f"(given value: {self.parameters['cluster_threshold']})."
            )
        if self.parameters["orig_input_data"] == "t1-freesurfer":
            self.parameters["custom_file"] = get_t1_freesurfer_custom_file()
            self.parameters["measure_label"] = "ct"
        elif self.parameters["orig_input_data"] == "pet-surface":
            self.parameters["custom_file"] = get_pet_surface_custom_file(
                self.parameters["acq_label"],
                self.parameters["suvr_reference_region"],
            )
            self.parameters["measure_label"] = self.parameters["acq_label"]
        else:
            if not all(
                [self.parameters["custom_file"], self.parameters["measure_label"]]
            ):
                raise ClinicaException(
                    "You must provide measure label (use the --measure_label option) "
                    "and a custom file (use the --custom_file option)."
                )

    def _check_custom_dependencies(self) -> None:
        """Check dependencies that can not be listed in the `info.json` file."""
        pass

    def get_input_fields(self) -> List[str]:
        """Specify the list of possible inputs of this pipeline.

        Returns
        -------
        list of str :
            A list of (string) input fields name.
        """
        return []

    def get_output_fields(self) -> List[str]:
        """Specify the list of possible outputs of this pipeline.

        Returns
        -------
        list of str :
            A list of (string) output fields name.
        """
        return ["output_dir"]

    def _build_input_node(self):
        """Build and connect an input node to the pipeline."""
        from clinica.utils.exceptions import ClinicaException
        from clinica.utils.inputs import clinica_list_of_files_reader

        # Check if already present in CAPS
        # ================================
        # Check if the group label has been existed, if yes, give an error to the users
        # Note(AR): if the user wants to compare Cortical Thickness measure with PET measure
        # using the group_id, Clinica won't allow it.
        # TODO: Modify this behaviour
        group_folder = self.caps_directory / "groups" / str(self.group_id)
        if group_folder.exists():
            raise ClinicaException(
                f"Group label {self.group_label} already exists (found in {group_folder})."
                "Please choose another one or delete the existing folder and "
                "also the working directory and rerun the pipeline."
            )

        # Check input files
        surface_query = []
        # clinica_files_reader expects regexp to start at subjects/ so sub-*/ses-*/ is removed here
        fwhm = str(self.parameters["full_width_at_half_maximum"])
        for direction, hemi in zip(["left", "right"], ["lh", "rh"]):
            cut_pattern = "sub-*/ses-*/"
            query = {"subject": "sub-*", "session": "ses-*", "hemi": hemi, "fwhm": fwhm}
            pattern_hemisphere = self.parameters["custom_file"] % query
            surface_based_info = {
                "pattern": pattern_hemisphere[
                    pattern_hemisphere.find(cut_pattern) + len(cut_pattern) :
                ],
                "description": f"surface-based features on {direction} hemisphere at FWHM = {fwhm}",
            }
            surface_query.append(surface_based_info)
        try:
            clinica_list_of_files_reader(
                self.subjects,
                self.sessions,
                self.caps_directory,
                surface_query,
            )
        except ClinicaException as e:
            raise RuntimeError(e)

    def _build_output_node(self):
        """Build and connect an output node to the pipeline."""
        import nipype.interfaces.utility as nutil
        import nipype.pipeline.engine as npe

        from ._utils import save_to_caps

        save_to_caps = npe.Node(
            interface=nutil.Function(
                input_names=[
                    "source_dir",
                    "caps_dir",
                    "overwrite_caps",
                    "group_id",
                    "glm_type",
                ],
                function=save_to_caps,
            ),
            name="SaveToCaps",
        )
        save_to_caps.inputs.caps_dir = self.caps_directory
        save_to_caps.inputs.overwrite_caps = self.overwrite_caps
        save_to_caps.inputs.group_id = self.group_id
        save_to_caps.inputs.glm_type = self.parameters["glm_type"]

        self.connect(
            [
                (self.output_node, save_to_caps, [("output_dir", "source_dir")]),
            ]
        )

    def _build_core_nodes(self):
        """Build and connect the core nodes of the pipeline."""
        import nipype.interfaces.utility as nutil
        import nipype.pipeline.engine as npe

        from ._utils import init_input_node, run_clinica_surfstat

        init_input = npe.Node(
            interface=nutil.Function(
                input_names=[
                    "parameters",
                    "group_id",
                    "base_dir",
                    "subjects_visits_tsv",
                ],
                output_names=["surfstat_results_dir"],
                function=init_input_node,
            ),
            name="0-InitPipeline",
        )
        init_input.inputs.parameters = self.parameters
        init_input.inputs.group_id = self.group_id
        init_input.inputs.base_dir = self.base_dir / self.name
        init_input.inputs.subjects_visits_tsv = self.tsv_file

        surfstat = npe.Node(
            name="RunSurfStat",
            interface=nutil.Function(
                input_names=[
                    "caps_dir",
                    "output_dir",
                    "subjects_visits_tsv",
                    "pipeline_parameters",
                    "group_label",
                ],
                output_names=["output_dir"],
                function=run_clinica_surfstat,
            ),
        )
        surfstat.inputs.caps_dir = self.caps_directory
        surfstat.inputs.subjects_visits_tsv = self.tsv_file
        surfstat.inputs.pipeline_parameters = self.parameters
        surfstat.inputs.group_label = self.group_label

        self.connect(
            [
                (init_input, surfstat, [("surfstat_results_dir", "output_dir")]),
                (surfstat, self.output_node, [("output_dir", "output_dir")]),
            ]
        )
