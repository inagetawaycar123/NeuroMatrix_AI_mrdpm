import * as react_jsx_runtime from 'react/jsx-runtime';
import { EditorOptions, Editor, MarkViewRendererOptions, MarkView, MarkViewProps, MarkViewRenderer, NodeViewProps, NodeViewRendererOptions, NodeView, NodeViewRendererProps, NodeViewRenderer } from '@tiptap/core';
export * from '@tiptap/core';
import * as React from 'react';
import React__default, { DependencyList, ReactNode, HTMLAttributes, HTMLProps, ForwardedRef, ComponentProps, ComponentClass, FunctionComponent, ForwardRefExoticComponent, PropsWithoutRef, RefAttributes, ComponentType as ComponentType$1 } from 'react';
import { Node } from '@tiptap/pm/model';
import { Decoration, DecorationSource } from '@tiptap/pm/view';
import { BubbleMenuPluginProps } from '@tiptap/extension-bubble-menu';
import { FloatingMenuPluginProps } from '@tiptap/extension-floating-menu';

/**
 * The options for the `useEditor` hook.
 */
type UseEditorOptions = Partial<EditorOptions> & {
    /**
     * Whether to render the editor on the first render.
     * If client-side rendering, set this to `true`.
     * If server-side rendering, set this to `false`.
     * @default true
     */
    immediatelyRender?: boolean;
    /**
     * Whether to re-render the editor on each transaction.
     * This is legacy behavior that will be removed in future versions.
     * @default false
     */
    shouldRerenderOnTransaction?: boolean;
};
/**
 * This hook allows you to create an editor instance.
 * @param options The editor options
 * @param deps The dependencies to watch for changes
 * @returns The editor instance
 * @example const editor = useEditor({ extensions: [...] })
 */
declare function useEditor(options: UseEditorOptions & {
    immediatelyRender: false;
}, deps?: DependencyList): Editor | null;
/**
 * This hook allows you to create an editor instance.
 * @param options The editor options
 * @param deps The dependencies to watch for changes
 * @returns The editor instance
 * @example const editor = useEditor({ extensions: [...] })
 */
declare function useEditor(options: UseEditorOptions, deps?: DependencyList): Editor;

type EditorContextValue = {
    editor: Editor | null;
};
declare const EditorContext: React__default.Context<EditorContextValue>;
declare const EditorConsumer: React__default.Consumer<EditorContextValue>;
/**
 * A hook to get the current editor instance.
 */
declare const useCurrentEditor: () => EditorContextValue;
type EditorProviderProps = {
    children?: ReactNode;
    slotBefore?: ReactNode;
    slotAfter?: ReactNode;
    editorContainerProps?: HTMLAttributes<HTMLDivElement>;
} & UseEditorOptions;
/**
 * This is the provider component for the editor.
 * It allows the editor to be accessible across the entire component tree
 * with `useCurrentEditor`.
 */
declare function EditorProvider({ children, slotAfter, slotBefore, editorContainerProps, ...editorOptions }: EditorProviderProps): react_jsx_runtime.JSX.Element | null;

interface EditorContentProps extends HTMLProps<HTMLDivElement> {
    editor: Editor | null;
    innerRef?: ForwardedRef<HTMLDivElement | null>;
}
declare class PureEditorContent extends React__default.Component<EditorContentProps, {
    hasContentComponentInitialized: boolean;
}> {
    editorContentRef: React__default.RefObject<any>;
    initialized: boolean;
    unsubscribeToContentComponent?: () => void;
    constructor(props: EditorContentProps);
    componentDidMount(): void;
    componentDidUpdate(): void;
    init(): void;
    componentWillUnmount(): void;
    render(): react_jsx_runtime.JSX.Element;
}
declare const EditorContent: React__default.NamedExoticComponent<Omit<EditorContentProps, "ref"> & React__default.RefAttributes<HTMLDivElement>>;

type NodeViewContentProps<T extends keyof React__default.JSX.IntrinsicElements = 'div'> = {
    as?: NoInfer<T>;
} & ComponentProps<T>;
declare function NodeViewContent<T extends keyof React__default.JSX.IntrinsicElements = 'div'>({ as: Tag, ...props }: NodeViewContentProps<T>): react_jsx_runtime.JSX.Element;

interface NodeViewWrapperProps {
    [key: string]: any;
    as?: React__default.ElementType;
}
declare const NodeViewWrapper: React__default.FC<NodeViewWrapperProps>;

interface ReactRendererOptions {
    /**
     * The editor instance.
     * @type {Editor}
     */
    editor: Editor;
    /**
     * The props for the component.
     * @type {Record<string, any>}
     * @default {}
     */
    props?: Record<string, any>;
    /**
     * The tag name of the element.
     * @type {string}
     * @default 'div'
     */
    as?: string;
    /**
     * The class name of the element.
     * @type {string}
     * @default ''
     * @example 'foo bar'
     */
    className?: string;
}
type ComponentType<R, P> = ComponentClass<P> | FunctionComponent<P> | ForwardRefExoticComponent<PropsWithoutRef<P> & RefAttributes<R>>;
/**
 * The ReactRenderer class. It's responsible for rendering React components inside the editor.
 * @example
 * new ReactRenderer(MyComponent, {
 *   editor,
 *   props: {
 *     foo: 'bar',
 *   },
 *   as: 'span',
 * })
 */
declare class ReactRenderer<R = unknown, P extends Record<string, any> = object> {
    id: string;
    editor: Editor;
    component: any;
    element: HTMLElement;
    props: P;
    reactElement: ReactNode;
    ref: R | null;
    /**
     * Flag to track if the renderer has been destroyed, preventing queued or asynchronous renders from executing after teardown.
     */
    destroyed: boolean;
    /**
     * Immediately creates element and renders the provided React component.
     */
    constructor(component: ComponentType<R, P>, { editor, props, as, className }: ReactRendererOptions);
    /**
     * Render the React component.
     */
    render(): void;
    /**
     * Re-renders the React component with new props.
     */
    updateProps(props?: Record<string, any>): void;
    /**
     * Destroy the React component.
     */
    destroy(): void;
    /**
     * Update the attributes of the element that holds the React component.
     */
    updateAttributes(attributes: Record<string, string>): void;
}

interface MarkViewContextProps {
    markViewContentRef: (element: HTMLElement | null) => void;
}
declare const ReactMarkViewContext: React__default.Context<MarkViewContextProps>;
type MarkViewContentProps<T extends keyof React__default.JSX.IntrinsicElements = 'span'> = {
    as?: T;
} & Omit<React__default.ComponentProps<T>, 'as'>;
declare const MarkViewContent: <T extends keyof React__default.JSX.IntrinsicElements = "span">(props: MarkViewContentProps<T>) => react_jsx_runtime.JSX.Element;
interface ReactMarkViewRendererOptions extends MarkViewRendererOptions {
    /**
     * The tag name of the element wrapping the React component.
     */
    as?: string;
    className?: string;
    attrs?: {
        [key: string]: string;
    };
}
declare class ReactMarkView extends MarkView<React__default.ComponentType<MarkViewProps>, ReactMarkViewRendererOptions> {
    renderer: ReactRenderer;
    contentDOMElement: HTMLElement;
    constructor(component: React__default.ComponentType<MarkViewProps>, props: MarkViewProps, options?: Partial<ReactMarkViewRendererOptions>);
    get dom(): HTMLElement;
    get contentDOM(): HTMLElement;
}
declare function ReactMarkViewRenderer(component: React__default.ComponentType<MarkViewProps>, options?: Partial<ReactMarkViewRendererOptions>): MarkViewRenderer;

type ReactNodeViewProps<T = HTMLElement> = NodeViewProps & {
    ref: React__default.RefObject<T | null>;
};

interface ReactNodeViewRendererOptions extends NodeViewRendererOptions {
    /**
     * This function is called when the node view is updated.
     * It allows you to compare the old node with the new node and decide if the component should update.
     */
    update: ((props: {
        oldNode: Node;
        oldDecorations: readonly Decoration[];
        oldInnerDecorations: DecorationSource;
        newNode: Node;
        newDecorations: readonly Decoration[];
        innerDecorations: DecorationSource;
        updateProps: () => void;
    }) => boolean) | null;
    /**
     * The tag name of the element wrapping the React component.
     */
    as?: string;
    /**
     * The class name of the element wrapping the React component.
     */
    className?: string;
    /**
     * Attributes that should be applied to the element wrapping the React component.
     * If this is a function, it will be called each time the node view is updated.
     * If this is an object, it will be applied once when the node view is mounted.
     */
    attrs?: Record<string, string> | ((props: {
        node: Node;
        HTMLAttributes: Record<string, any>;
    }) => Record<string, string>);
}
declare class ReactNodeView<T = HTMLElement, Component extends ComponentType$1<ReactNodeViewProps<T>> = ComponentType$1<ReactNodeViewProps<T>>, NodeEditor extends Editor = Editor, Options extends ReactNodeViewRendererOptions = ReactNodeViewRendererOptions> extends NodeView<Component, NodeEditor, Options> {
    /**
     * The renderer instance.
     */
    renderer: ReactRenderer<unknown, ReactNodeViewProps<T>>;
    /**
     * The element that holds the rich-text content of the node.
     */
    contentDOMElement: HTMLElement | null;
    /**
     * The requestAnimationFrame ID used for selection updates.
     */
    selectionRafId: number | null;
    constructor(component: Component, props: NodeViewRendererProps, options?: Partial<Options>);
    private cachedExtensionWithSyncedStorage;
    /**
     * Returns a proxy of the extension that redirects storage access to the editor's mutable storage.
     * This preserves the original prototype chain (instanceof checks, methods like configure/extend work).
     * Cached to avoid proxy creation on every update.
     */
    get extensionWithSyncedStorage(): NodeViewRendererProps['extension'];
    /**
     * Setup the React component.
     * Called on initialization.
     */
    mount(): void;
    /**
     * Return the DOM element.
     * This is the element that will be used to display the node view.
     */
    get dom(): HTMLElement;
    /**
     * Return the content DOM element.
     * This is the element that will be used to display the rich-text content of the node.
     */
    get contentDOM(): HTMLElement | null;
    /**
     * On editor selection update, check if the node is selected.
     * If it is, call `selectNode`, otherwise call `deselectNode`.
     */
    handleSelectionUpdate(): void;
    /**
     * On update, update the React component.
     * To prevent unnecessary updates, the `update` option can be used.
     */
    update(node: Node, decorations: readonly Decoration[], innerDecorations: DecorationSource): boolean;
    /**
     * Select the node.
     * Add the `selected` prop and the `ProseMirror-selectednode` class.
     */
    selectNode(): void;
    /**
     * Deselect the node.
     * Remove the `selected` prop and the `ProseMirror-selectednode` class.
     */
    deselectNode(): void;
    /**
     * Destroy the React component instance.
     */
    destroy(): void;
    /**
     * Update the attributes of the top-level element that holds the React component.
     * Applying the attributes defined in the `attrs` option.
     */
    updateElementAttributes(): void;
}
/**
 * Create a React node view renderer.
 */
declare function ReactNodeViewRenderer<T = HTMLElement>(component: ComponentType$1<ReactNodeViewProps<T>>, options?: Partial<ReactNodeViewRendererOptions>): NodeViewRenderer;

type Optional$1<T, K extends keyof T> = Pick<Partial<T>, K> & Omit<T, K>;
type BubbleMenuProps = Optional$1<Omit<Optional$1<BubbleMenuPluginProps, 'pluginKey'>, 'element'>, 'editor'> & React__default.HTMLAttributes<HTMLDivElement>;

type Optional<T, K extends keyof T> = Pick<Partial<T>, K> & Omit<T, K>;
type FloatingMenuProps = Omit<Optional<FloatingMenuPluginProps, 'pluginKey'>, 'element' | 'editor'> & {
    editor: FloatingMenuPluginProps['editor'] | null;
    options?: FloatingMenuPluginProps['options'];
} & React__default.HTMLAttributes<HTMLDivElement>;

/**
 * The shape of the React context used by the `<Tiptap />` components.
 *
 * This object exposes the editor instance and a simple readiness flag.
 */
type TiptapContextType = {
    /** The Tiptap editor instance. May be null during SSR or before initialization. */
    editor: Editor | null;
    /** True when the editor has finished initializing and is ready for user interaction. */
    isReady: boolean;
};
/**
 * React context that stores the current editor instance and readiness flag.
 *
 * Use `useTiptap()` to read from this context in child components.
 */
declare const TiptapContext: React.Context<TiptapContextType>;
/**
 * Hook to read the Tiptap context (`editor` + `isReady`).
 *
 * This is a small convenience wrapper around `useContext(TiptapContext)`.
 *
 * @returns The current `TiptapContextType` value from the provider.
 *
 * @example
 * ```tsx
 * import { useTiptap } from '@tiptap/react'
 *
 * function Status() {
 *   const { isReady } = useTiptap()
 *   return <div>{isReady ? 'Editor ready' : 'Loading editor...'}</div>
 * }
 * ```
 */
declare const useTiptap: () => TiptapContextType;
/**
 * Select a slice of the editor state using the context-provided editor.
 *
 * This is a thin wrapper around `useEditorState` that reads the `editor`
 * instance from `useTiptap()` so callers don't have to pass it manually.
 *
 * Important: This hook should only be used when the editor is available.
 * Use the `isReady` flag from `useTiptap()` to guard against null editor,
 * or ensure your component only renders after the editor is initialized.
 *
 * @typeParam TSelectorResult - The type returned by the selector.
 * @param selector - Function that receives the editor state snapshot and
 *                   returns the piece of state you want to subscribe to.
 * @param equalityFn - Optional function to compare previous/next selected
 *                     values and avoid unnecessary updates.
 * @returns The selected slice of the editor state.
 *
 * @example
 * ```tsx
 * function WordCount() {
 *   const { isReady } = useTiptap()
 *
 *   // Only use useTiptapState when the editor is ready
 *   const wordCount = useTiptapState(state => {
 *     const text = state.editor.state.doc.textContent
 *     return text.split(/\s+/).filter(Boolean).length
 *   })
 *
 *   if (!isReady) return null
 *
 *   return <span>{wordCount} words</span>
 * }
 * ```
 */
declare function useTiptapState<TSelectorResult>(selector: (context: EditorStateSnapshot<Editor>) => TSelectorResult, equalityFn?: (a: TSelectorResult, b: TSelectorResult | null) => boolean): TSelectorResult;
/**
 * Props for the `Tiptap` root/provider component.
 */
type TiptapWrapperProps = {
    /**
     * The editor instance to provide to child components.
     * Can be null during SSR or before initialization.
     */
    instance: Editor | null;
    children: ReactNode;
};
/**
 * Top-level provider component that makes the editor instance available via
 * React context and tracks when the editor becomes ready.
 *
 * The component listens to the editor's `create` event and flips the
 * `isReady` flag once initialization completes.
 *
 * This component also provides backwards compatibility with the legacy
 * `EditorContext`, so components using `useCurrentEditor()` will work
 * inside a `<Tiptap>` provider.
 *
 * @param props - Component props.
 * @returns A context provider element wrapping `children`.
 *
 * @example
 * ```tsx
 * import { Tiptap, useEditor } from '@tiptap/react'
 *
 * function App() {
 *   const editor = useEditor({ extensions: [...] })
 *
 *   return (
 *     <Tiptap instance={editor}>
 *       <Toolbar />
 *       <Tiptap.Content />
 *     </Tiptap>
 *   )
 * }
 * ```
 */
declare function TiptapWrapper({ instance, children }: TiptapWrapperProps): react_jsx_runtime.JSX.Element;
declare namespace TiptapWrapper {
    var displayName: string;
}
/**
 * Convenience component that renders `EditorContent` using the context-provided
 * editor instance. Use this instead of manually passing the `editor` prop.
 *
 * @param props - All `EditorContent` props except `editor` and `ref`.
 * @returns An `EditorContent` element bound to the context editor.
 *
 * @example
 * ```tsx
 * // inside a Tiptap provider
 * <Tiptap.Content className="editor" />
 * ```
 */
declare function TiptapContent({ ...rest }: Omit<EditorContentProps, 'editor' | 'ref'>): react_jsx_runtime.JSX.Element;
declare namespace TiptapContent {
    var displayName: string;
}
type TiptapLoadingProps = {
    children: ReactNode;
};
/**
 * Component that renders its children only when the editor is not ready.
 *
 * This is useful for displaying loading states or placeholders during
 * editor initialization, especially with SSR.
 *
 * @param props - The props for the TiptapLoading component.
 * @returns The children when editor is not ready, or null when ready.
 *
 * @example
 * ```tsx
 * <Tiptap instance={editor}>
 *   <Tiptap.Loading>
 *     <div className="skeleton">Loading editor...</div>
 *   </Tiptap.Loading>
 *   <Tiptap.Content />
 * </Tiptap>
 * ```
 */
declare function TiptapLoading({ children }: TiptapLoadingProps): ReactNode;
declare namespace TiptapLoading {
    var displayName: string;
}
/**
 * A wrapper around the library `BubbleMenu` that injects the editor from
 * context so callers don't need to pass the `editor` prop.
 *
 * Returns `null` when the editor is not available (for example during SSR).
 *
 * @param props - Props for the underlying `BubbleMenu` (except `editor`).
 * @returns A `BubbleMenu` bound to the context editor, or `null`.
 *
 * @example
 * ```tsx
 * <Tiptap.BubbleMenu tippyOptions={{ duration: 100 }}>
 *   <button onClick={() => editor.chain().focus().toggleBold().run()}>Bold</button>
 * </Tiptap.BubbleMenu>
 * ```
 */
declare function TiptapBubbleMenu({ children, ...rest }: {
    children: ReactNode;
} & Omit<BubbleMenuProps, 'editor'>): react_jsx_runtime.JSX.Element | null;
declare namespace TiptapBubbleMenu {
    var displayName: string;
}
/**
 * A wrapper around the library `FloatingMenu` that injects the editor from
 * context so callers don't need to pass the `editor` prop.
 *
 * Returns `null` when the editor is not available.
 *
 * @param props - Props for the underlying `FloatingMenu` (except `editor`).
 * @returns A `FloatingMenu` bound to the context editor, or `null`.
 *
 * @example
 * ```tsx
 * <Tiptap.FloatingMenu placement="top">
 *   <button onClick={() => editor.chain().focus().toggleItalic().run()}>Italic</button>
 * </Tiptap.FloatingMenu>
 * ```
 */
declare function TiptapFloatingMenu({ children, ...rest }: {
    children: ReactNode;
} & Omit<FloatingMenuProps, 'editor'>): react_jsx_runtime.JSX.Element | null;
declare namespace TiptapFloatingMenu {
    var displayName: string;
}
/**
 * Root `Tiptap` component. Use it as the provider for all child components.
 *
 * The exported object includes several helper subcomponents for common use
 * cases: `Content`, `Loading`, `BubbleMenu`, and `FloatingMenu`.
 *
 * This component provides both the new `TiptapContext` (accessed via `useTiptap()`)
 * and the legacy `EditorContext` (accessed via `useCurrentEditor()`) for
 * backwards compatibility.
 *
 * @example
 * ```tsx
 * const editor = useEditor({ extensions: [...] })
 *
 * return (
 *   <Tiptap instance={editor}>
 *     <Tiptap.Loading>Initializing editor...</Tiptap.Loading>
 *     <Tiptap.Content />
 *     <Tiptap.BubbleMenu>
 *       <button onClick={() => editor.chain().focus().toggleBold().run()}>Bold</button>
 *     </Tiptap.BubbleMenu>
 *   </Tiptap>
 * )
 * ```
 */
declare const Tiptap: typeof TiptapWrapper & {
    /**
     * The Tiptap Content component that renders the EditorContent with the editor instance from the context.
     * @see TiptapContent
     */
    Content: typeof TiptapContent;
    /**
     * The Tiptap Loading component that renders its children only when the editor is not ready.
     * @see TiptapLoading
     */
    Loading: typeof TiptapLoading;
    /**
     * The Tiptap BubbleMenu component that wraps the BubbleMenu from Tiptap and provides the editor instance from the context.
     * @see TiptapBubbleMenu
     */
    BubbleMenu: typeof TiptapBubbleMenu;
    /**
     * The Tiptap FloatingMenu component that wraps the FloatingMenu from Tiptap and provides the editor instance from the context.
     * @see TiptapFloatingMenu
     */
    FloatingMenu: typeof TiptapFloatingMenu;
};

type EditorStateSnapshot<TEditor extends Editor | null = Editor | null> = {
    editor: TEditor;
    transactionNumber: number;
};
type UseEditorStateOptions<TSelectorResult, TEditor extends Editor | null = Editor | null> = {
    /**
     * The editor instance.
     */
    editor: TEditor;
    /**
     * A selector function to determine the value to compare for re-rendering.
     */
    selector: (context: EditorStateSnapshot<TEditor>) => TSelectorResult;
    /**
     * A custom equality function to determine if the editor should re-render.
     * @default `deepEqual` from `fast-deep-equal`
     */
    equalityFn?: (a: TSelectorResult, b: TSelectorResult | null) => boolean;
};
/**
 * This hook allows you to watch for changes on the editor instance.
 * It will allow you to select a part of the editor state and re-render the component when it changes.
 * @example
 * ```tsx
 * const editor = useEditor({...options})
 * const { currentSelection } = useEditorState({
 *  editor,
 *  selector: snapshot => ({ currentSelection: snapshot.editor.state.selection }),
 * })
 */
declare function useEditorState<TSelectorResult>(options: UseEditorStateOptions<TSelectorResult, Editor>): TSelectorResult;
/**
 * This hook allows you to watch for changes on the editor instance.
 * It will allow you to select a part of the editor state and re-render the component when it changes.
 * @example
 * ```tsx
 * const editor = useEditor({...options})
 * const { currentSelection } = useEditorState({
 *  editor,
 *  selector: snapshot => ({ currentSelection: snapshot.editor.state.selection }),
 * })
 */
declare function useEditorState<TSelectorResult>(options: UseEditorStateOptions<TSelectorResult, Editor | null>): TSelectorResult | null;

interface ReactNodeViewContextProps {
    onDragStart?: (event: DragEvent) => void;
    nodeViewContentRef?: (element: HTMLElement | null) => void;
    /**
     * This allows you to add children into the NodeViewContent component.
     * This is useful when statically rendering the content of a node view.
     */
    nodeViewContentChildren?: ReactNode;
}
declare const ReactNodeViewContext: React.Context<ReactNodeViewContextProps>;
declare const ReactNodeViewContentProvider: ({ children, content }: {
    children: ReactNode;
    content: ReactNode;
}) => React.FunctionComponentElement<React.ProviderProps<ReactNodeViewContextProps>>;
declare const useReactNodeView: () => ReactNodeViewContextProps;

export { EditorConsumer, EditorContent, type EditorContentProps, EditorContext, type EditorContextValue, EditorProvider, type EditorProviderProps, type EditorStateSnapshot, MarkViewContent, type MarkViewContentProps, type MarkViewContextProps, NodeViewContent, type NodeViewContentProps, NodeViewWrapper, type NodeViewWrapperProps, PureEditorContent, ReactMarkView, ReactMarkViewContext, ReactMarkViewRenderer, type ReactMarkViewRendererOptions, ReactNodeView, ReactNodeViewContentProvider, ReactNodeViewContext, type ReactNodeViewContextProps, type ReactNodeViewProps, ReactNodeViewRenderer, type ReactNodeViewRendererOptions, ReactRenderer, type ReactRendererOptions, Tiptap, TiptapBubbleMenu, TiptapContent, TiptapContext, type TiptapContextType, TiptapFloatingMenu, TiptapLoading, type TiptapLoadingProps, TiptapWrapper, type TiptapWrapperProps, type UseEditorOptions, type UseEditorStateOptions, useCurrentEditor, useEditor, useEditorState, useReactNodeView, useTiptap, useTiptapState };
