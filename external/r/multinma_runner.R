#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  if (!requireNamespace("jsonlite", quietly = TRUE)) {
    stop("Package 'jsonlite' is required. Install with install.packages('jsonlite').")
  }
  if (!requireNamespace("multinma", quietly = TRUE)) {
    stop("Package 'multinma' is required. Install with install.packages('multinma').")
  }
  if (!requireNamespace("rstan", quietly = TRUE)) {
    stop("Package 'rstan' is required by this runner for MCMC diagnostics.")
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
    stop("Usage: multinma_runner.R --input <input.json> --output <output.json>")
  }
  out
}

to_named_number_list <- function(x) {
  out <- as.list(as.numeric(x))
  names(out) <- names(x)
  out
}

extract_target_row <- function(df, treatment) {
  if (all(c(".trtb", ".trta") %in% names(df))) {
    idx <- which(as.character(df$.trtb) == treatment)
    if (length(idx) > 0) {
      return(df[idx[1], , drop = FALSE])
    }
  }
  if (all(c("trtb", "trta") %in% names(df))) {
    idx <- which(as.character(df$trtb) == treatment)
    if (length(idx) > 0) {
      return(df[idx[1], , drop = FALSE])
    }
  }
  if (nrow(df) == 0) return(NULL)
  rn <- rownames(df)
  if (is.null(rn)) return(NULL)
  target <- grep(paste0("\\[", treatment, "\\]"), rn, value = FALSE)
  if (length(target) == 0) {
    target <- which(rn == treatment)
  }
  if (length(target) == 0) return(NULL)
  df[target[1], , drop = FALSE]
}

extract_mean_sd <- function(df) {
  mean_col <- if ("mean" %in% names(df)) "mean" else if ("Estimate" %in% names(df)) "Estimate" else NULL
  sd_col <- if ("sd" %in% names(df)) "sd" else if ("SD" %in% names(df)) "SD" else NULL
  if (is.null(mean_col) || is.null(sd_col)) {
    stop("Could not locate mean/sd columns in multinma summary output.")
  }
  c(effect = as.numeric(df[[mean_col]][1]), se = abs(as.numeric(df[[sd_col]][1])))
}

fit_nma <- function(network, likelihood, link, trt_effects) {
  adapt_delta <- if (identical(trt_effects, "random")) 0.99 else 0.95
  suppressWarnings(
    suppressMessages(
      multinma::nma(
        network,
        trt_effects = trt_effects,
        likelihood = likelihood,
        link = link,
        iter = 1200,
        warmup = 600,
        chains = 2,
        refresh = 0,
        seed = 123,
        adapt_delta = adapt_delta
      )
    )
  )
}

diagnose_fit <- function(fit) {
  sm <- as.data.frame(summary(fit))
  issues <- c()
  warnings <- c()

  max_rhat <- NA_real_
  min_bulk <- NA_real_
  min_tail <- NA_real_
  divergences <- NA_real_

  if ("Rhat" %in% names(sm)) {
    rhat <- suppressWarnings(as.numeric(sm$Rhat))
    if (length(rhat) > 0 && any(is.finite(rhat))) {
      max_rhat <- max(rhat[is.finite(rhat)])
      if (max_rhat > 1.01) {
        issues <- c(issues, paste0("max_rhat=", signif(max_rhat, 4), " > 1.01"))
      }
    }
  }
  if ("Bulk_ESS" %in% names(sm)) {
    bulk <- suppressWarnings(as.numeric(sm$Bulk_ESS))
    if (length(bulk) > 0 && any(is.finite(bulk))) {
      min_bulk <- min(bulk[is.finite(bulk)])
      if (min_bulk < 100) {
        issues <- c(issues, paste0("min_bulk_ess=", signif(min_bulk, 4), " < 100"))
      }
    }
  }
  if ("Tail_ESS" %in% names(sm)) {
    tail <- suppressWarnings(as.numeric(sm$Tail_ESS))
    if (length(tail) > 0 && any(is.finite(tail))) {
      min_tail <- min(tail[is.finite(tail)])
      if (min_tail < 100) {
        issues <- c(issues, paste0("min_tail_ess=", signif(min_tail, 4), " < 100"))
      }
    }
  }

  if ("stanfit" %in% names(fit)) {
    sampler <- try(rstan::get_sampler_params(fit$stanfit, inc_warmup = FALSE), silent = TRUE)
    if (!inherits(sampler, "try-error")) {
      divergences <- sum(vapply(sampler, function(mat) {
        if ("divergent__" %in% colnames(mat)) {
          sum(as.numeric(mat[, "divergent__"]))
        } else {
          0
        }
      }, numeric(1)))
      if (is.finite(divergences) && divergences > 0) {
        issues <- c(issues, paste0("divergent_transitions=", as.integer(divergences)))
      }
      treedepth_hits <- sum(vapply(sampler, function(mat) {
        if ("treedepth__" %in% colnames(mat)) {
          sum(as.numeric(mat[, "treedepth__"]) >= 10)
        } else {
          0
        }
      }, numeric(1)))
      if (is.finite(treedepth_hits) && treedepth_hits > 0) {
        warnings <- c(warnings, paste0("treedepth_hits=", as.integer(treedepth_hits)))
      }
    }
  }

  list(
    pass = length(issues) == 0,
    issues = issues,
    warnings = warnings,
    metrics = list(
      max_rhat = max_rhat,
      min_bulk_ess = min_bulk,
      min_tail_ess = min_tail,
      divergences = divergences
    )
  )
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
  random_effects <- isTRUE(analysis$random_effects)

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
  merged$study_id <- as.character(merged$study_id)
  merged$treatment_id <- as.character(merged$treatment_id)

  if (!(reference %in% merged$treatment_id)) {
    stop("Reference treatment is not present in input data.")
  }

  likelihood <- if (measure_type == "binary") "binomial" else "normal"
  link <- if (measure_type == "binary") "logit" else "identity"

  if (measure_type == "continuous") {
    if (any(is.na(merged$se))) {
      stop("Continuous outcomes require non-missing 'se'.")
    }
    network <- multinma::set_agd_arm(
      merged,
      study = study_id,
      trt = treatment_id,
      y = value,
      se = se,
      trt_ref = reference
    )
  } else if (measure_type == "binary") {
    network <- multinma::set_agd_arm(
      merged,
      study = study_id,
      trt = treatment_id,
      r = value,
      n = n,
      trt_ref = reference
    )
  } else {
    stop(paste("Unsupported measure_type:", measure_type))
  }

  warnings_out <- c()
  model_used <- "fixed"
  fit <- NULL
  diagnostics <- NULL

  if (random_effects) {
    fit_random <- fit_nma(network, likelihood, link, trt_effects = "random")
    diag_random <- diagnose_fit(fit_random)
    if (diag_random$pass) {
      fit <- fit_random
      diagnostics <- diag_random
      model_used <- "random"
    } else {
      warnings_out <- c(
        warnings_out,
        paste0(
          "random_model_failed_diagnostics: ",
          paste(diag_random$issues, collapse = "; ")
        )
      )
      fit_fixed <- fit_nma(network, likelihood, link, trt_effects = "fixed")
      diag_fixed <- diagnose_fit(fit_fixed)
      fit <- fit_fixed
      diagnostics <- diag_fixed
      model_used <- "fixed_fallback"
    }
  } else {
    fit <- fit_nma(network, likelihood, link, trt_effects = "fixed")
    diagnostics <- diagnose_fit(fit)
    model_used <- "fixed"
  }

  if (!diagnostics$pass) {
    stop(
      paste0(
        "Multinma diagnostics failed: ",
        paste(diagnostics$issues, collapse = "; ")
      )
    )
  }

  trts <- sort(unique(merged$treatment_id))
  rel_ref_df <- as.data.frame(
    multinma::relative_effects(
      fit,
      trt_ref = reference,
      summary = TRUE,
      all_contrasts = FALSE
    )
  )
  te_vs_ref <- c()
  se_vs_ref <- c()
  for (trt in trts) {
    if (identical(trt, reference)) {
      te_vs_ref[[trt]] <- 0.0
      se_vs_ref[[trt]] <- 0.0
    } else {
      target <- extract_target_row(rel_ref_df, trt)
      if (is.null(target)) {
        stop(paste("Could not extract relative effect for treatment", trt))
      }
      stats <- extract_mean_sd(target)
      te_vs_ref[[trt]] <- stats[["effect"]]
      se_vs_ref[[trt]] <- stats[["se"]]
    }
  }

  contrast_out <- list()
  if (!is.null(requested) && nrow(requested) > 0) {
    for (i in seq_len(nrow(requested))) {
      numerator <- as.character(requested[i, 1])
      denominator <- as.character(requested[i, 2])
      label <- paste0(numerator, "_vs_", denominator)
      if (identical(numerator, denominator)) {
        contrast_out[[label]] <- list(effect = 0.0, se = 0.0)
      } else {
        rel <- multinma::relative_effects(
          fit,
          trt_ref = denominator,
          summary = TRUE,
          all_contrasts = FALSE
        )
        rel_df <- as.data.frame(rel)
        target <- extract_target_row(rel_df, numerator)
        if (is.null(target)) {
          stop(paste("Could not extract contrast", label))
        }
        stats <- extract_mean_sd(target)
        contrast_out[[label]] <- list(effect = stats[["effect"]], se = stats[["se"]])
      }
    }
  }

  output <- list(
    treatment_effects = to_named_number_list(te_vs_ref),
    treatment_ses = to_named_number_list(se_vs_ref),
    contrasts = contrast_out,
    diagnostics = list(
      pass = diagnostics$pass,
      issues = as.list(diagnostics$issues),
      warnings = as.list(c(diagnostics$warnings, warnings_out)),
      metrics = diagnostics$metrics
    ),
    model = list(
      package = "multinma",
      trt_effects = model_used
    )
  )
  jsonlite::write_json(output, parsed$output, auto_unbox = TRUE, pretty = TRUE)
}

main()

