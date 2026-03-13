#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  if (!requireNamespace("jsonlite", quietly = TRUE)) {
    stop("Package 'jsonlite' is required. Install with install.packages('jsonlite').")
  }
  if (!requireNamespace("meta", quietly = TRUE)) {
    stop("Package 'meta' is required. Install with install.packages('meta').")
  }
  if (!requireNamespace("netmeta", quietly = TRUE)) {
    stop("Package 'netmeta' is required. Install with install.packages('netmeta').")
  }
})

parse_args <- function(args) {
  out <- list(input = NULL, output = NULL)
  i <- 1
  while (i <= length(args)) {
    key <- args[[i]]
    if (key %in% c("--input", "--output")) {
      if (i + 1 > length(args)) {
        stop(paste("Missing value for", key))
      }
      val <- args[[i + 1]]
      if (key == "--input") out$input <- val
      if (key == "--output") out$output <- val
      i <- i + 2
    } else {
      i <- i + 1
    }
  }
  if (is.null(out$input) || is.null(out$output)) {
    stop("Usage: netmeta_runner.R --input <input.json> --output <output.json>")
  }
  out
}

as_num <- function(x) {
  as.numeric(x)
}

to_named_number_list <- function(x) {
  out <- as.list(as.numeric(x))
  names(out) <- names(x)
  out
}

extract_matrix_entry <- function(mat, row_name, col_name) {
  if (!is.matrix(mat)) {
    stop("Expected a matrix for treatment effects.")
  }
  rn <- rownames(mat)
  cn <- colnames(mat)
  if (is.null(rn) || is.null(cn)) {
    stop("Treatment matrix is missing row/column names.")
  }
  if (!(row_name %in% rn) || !(col_name %in% cn)) {
    stop(paste("Contrast not available in matrix:", row_name, "vs", col_name))
  }
  as.numeric(mat[row_name, col_name])
}

main <- function() {
  parsed <- parse_args(commandArgs(trailingOnly = TRUE))
  payload <- jsonlite::fromJSON(parsed$input, simplifyDataFrame = TRUE)

  analysis <- payload$analysis
  data <- payload$data
  requested <- payload$requested_contrasts

  outcome_id <- as.character(analysis$outcome_id)
  measure_type <- as.character(analysis$measure_type)
  reference <- as.character(analysis$reference_treatment)

  arms <- as.data.frame(data$arms, stringsAsFactors = FALSE)
  outcomes <- as.data.frame(data$outcomes_ad, stringsAsFactors = FALSE)

  out_rows <- outcomes[
    outcomes$outcome_id == outcome_id & outcomes$measure_type == measure_type,
    c("study_id", "arm_id", "value", "se"),
    drop = FALSE
  ]
  if (nrow(out_rows) < 2) {
    stop("Insufficient outcome rows for requested outcome.")
  }

  arm_rows <- arms[, c("study_id", "arm_id", "treatment_id", "n"), drop = FALSE]
  merged <- merge(out_rows, arm_rows, by = c("study_id", "arm_id"), all.x = TRUE, sort = FALSE)
  if (any(is.na(merged$treatment_id))) {
    stop("Some outcomes could not be matched to arm treatment IDs.")
  }

  sm <- if (measure_type == "binary") "OR" else "MD"
  if (measure_type == "continuous") {
    if (any(is.na(merged$se))) {
      stop("Continuous outcomes require non-missing 'se'.")
    }
    merged$sd <- as_num(merged$se) * sqrt(as_num(merged$n))
    pw <- meta::pairwise(
      treat = treatment_id,
      mean = value,
      sd = sd,
      n = n,
      studlab = study_id,
      data = merged,
      sm = sm
    )
  } else if (measure_type == "binary") {
    pw <- meta::pairwise(
      treat = treatment_id,
      event = value,
      n = n,
      studlab = study_id,
      data = merged,
      sm = sm
    )
  } else {
    stop(paste("Unsupported measure_type:", measure_type))
  }

  fit <- netmeta::netmeta(
    TE,
    seTE,
    treat1,
    treat2,
    studlab,
    data = pw,
    sm = sm,
    reference.group = reference,
    common = TRUE,
    random = TRUE
  )

  te_mat <- fit$TE.random
  se_mat <- fit$seTE.random
  if (is.null(te_mat) || is.null(se_mat)) {
    te_mat <- fit$TE.common
    se_mat <- fit$seTE.common
  }
  if (is.null(te_mat) || is.null(se_mat)) {
    stop("Could not extract effect matrices from netmeta fit.")
  }

  trts <- sort(unique(as.character(merged$treatment_id)))
  te_vs_ref <- c()
  se_vs_ref <- c()
  for (trt in trts) {
    if (identical(trt, reference)) {
      te_vs_ref[[trt]] <- 0.0
      se_vs_ref[[trt]] <- 0.0
    } else {
      te_vs_ref[[trt]] <- extract_matrix_entry(te_mat, trt, reference)
      se_vs_ref[[trt]] <- abs(extract_matrix_entry(se_mat, trt, reference))
    }
  }

  contrast_out <- list()
  if (!is.null(requested) && nrow(requested) > 0) {
    for (i in seq_len(nrow(requested))) {
      numerator <- as.character(requested[i, 1])
      denominator <- as.character(requested[i, 2])
      label <- paste0(numerator, "_vs_", denominator)
      eff <- extract_matrix_entry(te_mat, numerator, denominator)
      se <- abs(extract_matrix_entry(se_mat, numerator, denominator))
      contrast_out[[label]] <- list(effect = eff, se = se)
    }
  }

  output <- list(
    treatment_effects = to_named_number_list(te_vs_ref),
    treatment_ses = to_named_number_list(se_vs_ref),
    contrasts = contrast_out,
    diagnostics = list(
      pass = TRUE,
      issues = list(),
      warnings = list()
    ),
    model = list(
      package = "netmeta",
      trt_effects = "random"
    )
  )
  jsonlite::write_json(output, parsed$output, auto_unbox = TRUE, pretty = TRUE)
}

main()
