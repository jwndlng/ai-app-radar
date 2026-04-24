# Specification: Pipeline Task Runtime

## Purpose

TBD — Generic queue/worker runtime that executes any `BaseTask` concurrently, handling shuffled item ordering, periodic checkpointing, and staggered worker starts.

## Requirements

### Requirement: PipelineRuntime executes any BaseTask via a generic queue/worker loop
The `PipelineRuntime` SHALL accept any `BaseTask` instance and execute it by loading items from the producer, distributing them across N concurrent workers, calling the consumer's lifecycle hooks, and ensuring the store is persisted at completion.

#### Scenario: Items are shuffled before workers start
- **WHEN** `PipelineRuntime.run()` is called
- **THEN** the items returned by `producer.produce()` SHALL be shuffled in random order before any worker receives an item

#### Scenario: N workers process items concurrently
- **WHEN** the runtime starts with `concurrency=N`
- **THEN** up to N items SHALL be in-flight simultaneously, each handled by a separate asyncio worker

#### Scenario: Consumer.checkpoint() called every N completed items
- **WHEN** the count of completed items (success or failure) is a multiple of `task.checkpoint_every`
- **THEN** the runtime SHALL call `consumer.checkpoint()` to persist the current state snapshot to disk

#### Scenario: Consumer.finalize() called after all items processed
- **WHEN** all items have been dequeued and processed
- **THEN** the runtime SHALL call `consumer.finalize()` before returning, allowing post-processing such as dedup/ingest

#### Scenario: Empty producer causes immediate clean exit
- **WHEN** `producer.produce()` returns an empty list
- **THEN** the runtime SHALL log a warning and return without spawning workers

### Requirement: BaseTask defines the stage contract
Each pipeline stage SHALL implement `BaseTask[T]` by providing a producer that yields items and a consumer that processes one item. The task also declares default runtime parameters.

#### Scenario: Producer provides the full item list before processing starts
- **WHEN** `PipelineRuntime` calls `producer.produce()`
- **THEN** the producer SHALL return the complete list of items to process in this run; no items SHALL be added to the queue after the run begins

#### Scenario: Consumer processes one item atomically
- **WHEN** a worker dequeues an item and calls `consumer.consume(item)`
- **THEN** the consumer SHALL fully handle that item (fetch, extract, score, mutate, log) within the single call and NOT share mutable state with other concurrent workers

#### Scenario: Consumer persists a state snapshot on checkpoint
- **WHEN** `consumer.checkpoint()` is called by the runtime
- **THEN** the consumer SHALL write the current in-memory state to disk (e.g. `store.save(all_apps)`) so that a crash after the checkpoint loses at most `checkpoint_every` items of work

#### Scenario: Consumer.checkpoint() is a no-op when persistence is not needed
- **WHEN** a consumer has no intermediate state to persist (e.g. ScoutConsumer before ingest)
- **THEN** `checkpoint()` SHALL complete without error and without writing to disk

### Requirement: Staggered worker starts when start_gap is configured
When a task sets `start_gap`, the runtime SHALL introduce a random delay between worker launches to avoid bursty outbound requests.

#### Scenario: Workers start with a random delay within the configured range
- **WHEN** `task.start_gap = (min_s, max_s)` and N workers are spawned
- **THEN** each worker SHALL wait a random duration in `[min_s, max_s]` before making its first outbound request, distributed across workers so they do not all start simultaneously

#### Scenario: No delay when start_gap is None
- **WHEN** `task.start_gap` is `None`
- **THEN** workers SHALL begin processing immediately without any imposed delay
