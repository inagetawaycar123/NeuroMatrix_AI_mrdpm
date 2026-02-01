import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Link from '@tiptap/extension-link'
import Image from '@tiptap/extension-image'
import React from 'react'
import '../styles/editor.css'

interface RichTextEditorProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
}

export const RichTextEditor: React.FC<RichTextEditorProps> = ({
  value,
  onChange,
  placeholder = '输入内容...'
}) => {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        paragraph: {
          HTMLAttributes: {
            class: 'editor-paragraph'
          }
        },
        bulletList: {
          HTMLAttributes: {
            class: 'editor-list'
          }
        },
        orderedList: {
          HTMLAttributes: {
            class: 'editor-list'
          }
        }
      }),
      Link.configure({
        openOnClick: false,
        HTMLAttributes: {
          class: 'editor-link'
        }
      }),
      Image.configure({
        HTMLAttributes: {
          class: 'editor-image'
        }
      })
    ],
    content: value || `<p>${placeholder}</p>`,
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML())
    }
  })

  if (!editor) {
    return <div>编辑器加载中...</div>
  }

  const addImage = () => {
    const url = prompt('输入图片URL:')
    if (url) {
      editor.chain().focus().setImage({ src: url }).run()
    }
  }

  const addLink = () => {
    const url = prompt('输入链接URL:')
    if (url) {
      editor
        .chain()
        .focus()
        .extendMarkRange('link')
        .setLink({ href: url })
        .run()
    }
  }

  return (
    <div className="rich-text-editor">
      <div className="editor-toolbar">
        <button
          onClick={() => editor.chain().focus().toggleBold().run()}
          className={`format-btn ${editor.isActive('bold') ? 'active' : ''}`}
          title="加粗 (Ctrl+B)"
        >
          <strong>B</strong>
        </button>
        <button
          onClick={() => editor.chain().focus().toggleItalic().run()}
          className={`format-btn ${editor.isActive('italic') ? 'active' : ''}`}
          title="斜体 (Ctrl+I)"
        >
          <em>I</em>
        </button>
        <button
          onClick={() => editor.chain().focus().toggleStrike().run()}
          className={`format-btn ${editor.isActive('strike') ? 'active' : ''}`}
          title="删除线"
        >
          <s>S</s>
        </button>

        <div className="toolbar-divider" />

        <button
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
          className={`format-btn ${editor.isActive('heading', { level: 2 }) ? 'active' : ''}`}
          title="标题"
        >
          H2
        </button>
        <button
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          className={`format-btn ${editor.isActive('bulletList') ? 'active' : ''}`}
          title="列表"
        >
          •
        </button>
        <button
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          className={`format-btn ${editor.isActive('orderedList') ? 'active' : ''}`}
          title="有序列表"
        >
          1.
        </button>

        <div className="toolbar-divider" />

        <button onClick={addLink} className="format-btn" title="插入链接">
          🔗
        </button>
        <button onClick={addImage} className="format-btn" title="插入图片">
          🖼️
        </button>

        <div className="toolbar-divider" />

        <button
          onClick={() => editor.chain().focus().undo().run()}
          className="format-btn"
          title="撤销"
        >
          ↶
        </button>
        <button
          onClick={() => editor.chain().focus().redo().run()}
          className="format-btn"
          title="重做"
        >
          ↷
        </button>
      </div>

      <EditorContent editor={editor} className="editor-content" />
    </div>
  )
}
